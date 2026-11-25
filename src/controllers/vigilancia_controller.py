"""CONTROLADOR de vigilancia: alertas a la policía, cierres temporales,
reclamaciones de los propietarios, log de incidencias y notificaciones.

QUIÉN PUEDE HACER QUÉ
    Autoridad (policía):
        - recibe una notificación cuando un bar llega a niveles peligrosos (rojo)
        - cierra temporalmente un bar (antes tiene que escribir el motivo)
        - reabre un bar
        - decide si una reclamación es "Justificado" o "No justificado"
    Propietario:
        - recibe una notificación si cierran su bar, con el motivo que escribió la policía
        - puede presentar UNA reclamación por cada cierre
        - ve el log de incidencias de su bar
    Autoridad: ve el log de incidencias de todos los bares

Las funciones que cambian algo devuelven "" si todo ha ido bien, o un texto
con el error (igual que LocalController).
"""
# Datos de vigilancia (incidencias, cierres y notificaciones). "as datos" le pone un nombre corto.
from src.models import vigilancia as datos

# Para que los cambios que van juntos se guarden todos o ninguno.
from src.models.base_datos import transaccion

# Para poner la fecha de ahora.
from src.controllers.sensor_controller import fecha_actual

# Para saber los locales que existen.
from src.models.local import cargar_locales

# Mínimo de letras que debe tener el motivo de un cierre (para que sea una explicación de verdad).
MINIMO_LETRAS_MOTIVO = 20

# Tipos de incidencia que aparecen en el log.
TIPO_PELIGRO = "Nivel peligroso"
TIPO_NORMALIZADO = "Niveles normalizados"
TIPO_CIERRE = "Cierre temporal"
TIPO_REAPERTURA = "Reapertura"
TIPO_RECLAMACION = "Reclamación"
TIPO_RESOLUCION = "Resolución de reclamación"
TIPOS_INCIDENCIA = [
    TIPO_PELIGRO, TIPO_NORMALIZADO, TIPO_CIERRE, TIPO_REAPERTURA, TIPO_RECLAMACION, TIPO_RESOLUCION
]


def nombre_policia(usuario):
    """Texto que identifica al policía. Ejemplo: "Ayuntamiento Demo (POL-0001)"."""
    return f"{usuario.nombre} ({usuario.id_policial})"


class VigilanciaController:
    # ------------------------------------------------------------------
    # LOG DE INCIDENCIAS
    # ------------------------------------------------------------------
    def apuntar_incidencia(self, codigo, tipo, autor, descripcion):
        """Añade una línea al log de incidencias de un bar."""
        datos.guardar_incidencia(codigo, fecha_actual(), tipo, autor, descripcion)

    def incidencias_de(self, codigo):
        """Log de incidencias de un bar, de la más nueva a la más antigua."""
        return list(datos.incidencias_de(codigo))

    def todas_las_incidencias(self, tipo, cantidad):
        """(Autoridad) Las últimas incidencias de toda la zona. tipo="" significa todos los tipos."""
        return list(datos.ultimas_incidencias(tipo, cantidad))

    # ------------------------------------------------------------------
    # NOTIFICACIONES
    # ------------------------------------------------------------------
    def notificar(self, para, titulo, mensaje):
        """Crea un aviso. "para" es el código de un local o None (para la Autoridad)."""
        datos.guardar_notificacion(para, fecha_actual(), titulo, mensaje)

    def notificaciones_de(self, usuario):
        """Avisos de un usuario, del más nuevo al más antiguo."""
        if usuario.rol == "Autoridad":
            return list(datos.notificaciones_de(None))
        if usuario.rol == "Propietario" and usuario.codigo_negocio:
            return list(datos.notificaciones_de(usuario.codigo_negocio))
        # Los vecinos no reciben avisos.
        return []

    def sin_leer(self, usuario):
        """Cuántos avisos no ha leído todavía el usuario."""
        total = 0
        for aviso in self.notificaciones_de(usuario):
            if not aviso["leida"]:
                total = total + 1
        return total

    def marcar_leidas(self, usuario):
        """Marca como leídos todos los avisos del usuario."""
        if usuario.rol == "Autoridad":
            datos.marcar_leidas(None)
        elif usuario.rol == "Propietario" and usuario.codigo_negocio:
            datos.marcar_leidas(usuario.codigo_negocio)

    # ------------------------------------------------------------------
    # ALERTAS AUTOMÁTICAS (niveles peligrosos)
    # ------------------------------------------------------------------
    def alerta_abierta(self, codigo):
        """True si el bar tiene una alerta de peligro que aún no se ha normalizado.

        Miramos la última incidencia automática del bar: si es "Nivel peligroso",
        la alerta sigue abierta; si es "Niveles normalizados" (o no hay), no.
        """
        # Van de la más nueva a la más antigua: la primera automática que sale es la última que hubo.
        for incidencia in self.incidencias_de(codigo):
            if incidencia["tipo"] in (TIPO_PELIGRO, TIPO_NORMALIZADO):
                return incidencia["tipo"] == TIPO_PELIGRO
        return False

    def revisar_alertas(self, sensor_controller):
        """Revisa todos los bares después de cada medida.

        - Si un bar pasa a ROJO: se apunta en su log y se avisa a la policía.
        - Si un bar que estaba en rojo se normaliza: se apunta en su log.
        """
        for local in cargar_locales():
            codigo = local.codigo
            en_peligro = sensor_controller.color_bar(codigo) == "rojo"
            ya_avisado = self.alerta_abierta(codigo)

            if en_peligro and not ya_avisado:
                # Texto con los valores actuales, para que la policía sepa qué pasa.
                detalle = sensor_controller.texto_valores(codigo)
                with transaccion():
                    self.apuntar_incidencia(codigo, TIPO_PELIGRO, "Sistema de sensores", detalle)
                    self.notificar(None, f"Niveles peligrosos en {local.nombre} ({codigo})", detalle)

            if not en_peligro and ya_avisado:
                self.apuntar_incidencia(
                    codigo, TIPO_NORMALIZADO, "Sistema de sensores", "Los sensores vuelven a valores seguros."
                )

    # ------------------------------------------------------------------
    # CIERRES TEMPORALES
    # ------------------------------------------------------------------
    def cierre_activo(self, codigo):
        """El cierre que tiene ahora mismo el bar, o None si está abierto."""
        return datos.cierre_activo(codigo)

    def ultimo_cierre(self, codigo):
        """El último cierre que ha tenido el bar (activo o no), o None si nunca lo han cerrado."""
        return datos.ultimo_cierre(codigo)

    def cerrados(self):
        """Lista de todos los cierres activos (bares cerrados ahora mismo)."""
        return datos.cierres_activos()

    def cerrar_local(self, usuario, codigo, motivo):
        """La policía cierra temporalmente un bar. El motivo es obligatorio."""
        # 1. Solo la Autoridad.
        if usuario.rol != "Autoridad":
            return "Solo la policía puede cerrar un local."
        # 2. El motivo tiene que estar escrito y explicar algo.
        motivo = motivo.strip()
        if len(motivo) < MINIMO_LETRAS_MOTIVO:
            return f"Escribe el motivo del cierre (mínimo {MINIMO_LETRAS_MOTIVO} letras)."
        # 3. No se puede cerrar un bar que ya está cerrado.
        if self.cierre_activo(codigo):
            return "Este local ya está cerrado."
        # 4. El cierre, el log del bar y el aviso al propietario: todo o nada.
        with transaccion():
            datos.guardar_cierre(codigo, fecha_actual(), nombre_policia(usuario), motivo)
            self.apuntar_incidencia(codigo, TIPO_CIERRE, nombre_policia(usuario), motivo)
            self.notificar(
                codigo,
                "Tu local ha sido cerrado temporalmente",
                f"Motivo escrito por la policía: {motivo} "
                f"Si crees que no está justificado, puedes presentar una reclamación.",
            )
        return ""

    def reabrir_local(self, usuario, codigo, nota):
        """La policía vuelve a abrir un bar cerrado."""
        if usuario.rol != "Autoridad":
            return "Solo la policía puede reabrir un local."
        cierre = self.cierre_activo(codigo)
        if cierre is None:
            return "Este local no está cerrado."
        texto = nota.strip() or "El local puede volver a abrir."
        cierre["activo"] = 0
        with transaccion():
            datos.actualizar_cierre(cierre)
            self.apuntar_incidencia(codigo, TIPO_REAPERTURA, nombre_policia(usuario), texto)
            self.notificar(codigo, "Tu local ya puede volver a abrir", texto)
        return ""

    # ------------------------------------------------------------------
    # RECLAMACIONES
    # ------------------------------------------------------------------
    def reclamar(self, usuario, codigo, texto):
        """El propietario reclama un cierre que cree injustificado."""
        # 1. Solo el propietario de ESE local.
        if usuario.rol != "Propietario" or usuario.codigo_negocio != codigo:
            return "Solo el propietario del local puede reclamar."
        texto = texto.strip()
        if not texto:
            return "Escribe por qué crees que el cierre no está justificado."
        cierre = self.cierre_activo(codigo)
        if cierre is None:
            return "Tu local no está cerrado."
        # 2. Solo una reclamación por cierre.
        if cierre["estado_reclamacion"]:
            return "Ya has presentado una reclamación para este cierre."
        # 3. La guardamos como "Pendiente", con su log y el aviso a la policía.
        cierre["reclamacion"] = texto
        cierre["estado_reclamacion"] = "Pendiente"
        with transaccion():
            datos.actualizar_cierre(cierre)
            self.apuntar_incidencia(codigo, TIPO_RECLAMACION, usuario.nombre, texto)
            self.notificar(None, f"Nueva reclamación del local {codigo}", texto)
        return ""

    def reclamaciones_pendientes(self):
        """Cierres con una reclamación que la policía aún no ha valorado."""
        return datos.cierres_con_reclamacion_pendiente()

    def resolver_reclamacion(self, usuario, codigo, justificado, respuesta):
        """La policía valora una reclamación.

        justificado = True  -> el cierre estaba bien hecho: el local sigue cerrado.
        justificado = False -> el cierre no estaba justificado: el local se reabre.
        """
        if usuario.rol != "Autoridad":
            return "Solo la policía puede valorar reclamaciones."
        respuesta = respuesta.strip()
        if not respuesta:
            return "Escribe una respuesta para el propietario."
        pendientes = list(datos.cierres_con_reclamacion_pendiente(codigo))
        if not pendientes:
            return "No hay ninguna reclamación pendiente de este local."
        cierre = pendientes[0]
        cierre["respuesta"] = respuesta
        if justificado:
            cierre["estado_reclamacion"] = "Justificado"
            titulo = "Reclamación rechazada: el cierre está justificado"
        else:
            cierre["estado_reclamacion"] = "No justificado"
            # El cierre no era justo: el local se reabre.
            cierre["activo"] = 0
            titulo = "Reclamación aceptada: tu local puede volver a abrir"
        with transaccion():
            datos.actualizar_cierre(cierre)
            self.apuntar_incidencia(
                codigo, TIPO_RESOLUCION, nombre_policia(usuario), f"{cierre['estado_reclamacion']}. {respuesta}"
            )
            self.notificar(codigo, titulo, respuesta)
        return ""
