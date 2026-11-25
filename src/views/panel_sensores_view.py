"""VISTA: panel principal (dashboard). Lo que se ve depende del rol:

    Vecino       -> ruido y aforo de los bares de SU calle.
    Propietario  -> notificaciones, estado de SU local (con la opción de reclamar
                    un cierre), sus sensores y su log de incidencias.
    Autoridad    -> resumen de la zona, notificaciones, alertas, reclamaciones,
                    bares cerrados, comparación de bares y log de toda la zona.
    Todos        -> la lista de bares con su semáforo, del más al menos peligroso.
"""
# Flet es la librería que dibuja la interfaz gráfica.
import flet as ft

# Colores del semáforo, del mejor al peor.
from src.controllers.sensor_controller import COLORES
from src.controllers.vigilancia_controller import TIPOS_INCIDENCIA

# Nombres y unidades de los sensores.
from src.models.sensor import NOMBRE_SENSOR, TIPOS_SENSOR, TIPOS_VECINO, UNIDAD_SENSOR

# Piezas que se repiten en varias pantallas.
from src.views.piezas_sensores import (
    SIGNIFICADO,
    cabecera,
    estado_bar,
    etiqueta_cerrado,
    fila_leds,
    grafico_barras,
    icono_semaforo,
    pedir_cierre,
    pedir_reapertura,
    seccion,
    tabla_incidencias,
    tarjeta_sensor,
    ventana_texto,
)

# Frase que explica a cada rol qué puede hacer.
DESCRIPCION_ROL = {
    "Vecino": "Puedes consultar el ruido y el aforo de los bares de tu calle y el estado de la zona.",
    "Propietario": "Puedes ver los sensores de tu local y mantener actualizados sus datos.",
    "Autoridad": "Puedes gestionar los locales y supervisar los sensores de toda la zona.",
}

# Texto del botón que lleva a la pantalla de locales, distinto para cada rol.
TEXTO_BOTON_LOCALES = {
    "Vecino": "Ver locales de la zona",
    "Propietario": "Ver locales y editar el mío",
    "Autoridad": "Gestionar locales",
}

# Cuántas notificaciones e incidencias se enseñan como máximo.
MAXIMO_AVISOS = 8
MAXIMO_INCIDENCIAS = 15


def desplegable(titulo, opciones, elegida, al_elegir):
    """Desplegable. "opciones" es un diccionario {valor: texto que se ve}."""
    lista = []
    for valor in opciones:
        lista.append(ft.DropdownOption(key=valor, text=opciones[valor]))
    return ft.Dropdown(label=titulo, width=240, options=lista, value=elegida, on_select=al_elegir)


class PanelSensoresView:
    def __init__(self, app):
        self.app = app
        self.usuario = app.usuario
        # Atajos para no escribir "self.app." todo el rato.
        self.sensores = app.sensor_controller
        self.vigilancia = app.vigilancia_controller
        self.locales = app.local_controller

    # ------------------------------------------------------------------
    # PARA TODOS
    # ------------------------------------------------------------------
    def tarjeta_bar(self, local):
        """Tarjeta pequeña de un bar. Los sensores solo salen si el usuario puede verlos."""
        controles = [
            ft.Text(local.nombre, size=18, weight=ft.FontWeight.BOLD),
            ft.Text(f"{local.codigo} · {local.direccion}", size=12),
            estado_bar(self.app, local.codigo),
        ]
        if self.locales.puede_ver_sensores(self.usuario, local):
            controles = controles + [
                ft.Text(self.sensores.texto_valores(local.codigo), size=13),
                fila_leds(self.app, local.codigo, 18),
                ft.TextButton(
                    "Ver sensores e incidencias",
                    icon=ft.Icons.SENSORS,
                    # Al pulsar se abre la pantalla de detalle de ESTE bar.
                    on_click=lambda evento: self.app.ir_a_bar(local),
                ),
            ]
        return ft.Card(
            # 1 tarjeta por fila en móvil, 2 en tablet, 3 en pantalla grande.
            col={"xs": 12, "sm": 6, "lg": 4},
            content=ft.Container(padding=16, content=ft.Column(controls=controles)),
        )

    def bares_ordenados(self):
        """Los bares del más peligroso al menos peligroso."""
        # sorted() ordena según lo que devuelve "key" (la posición del color); reverse=True, de mayor a menor.
        return sorted(
            self.locales.listar(),
            key=lambda local: COLORES.index(self.sensores.color_bar(local.codigo)),
            reverse=True,
        )

    def filtrar_bares(self, evento=None):
        """Vuelve a llenar la lista de bares según el buscador y el filtro de estado."""
        texto = (self.buscador.value or "").lower()
        tarjetas = []
        for local in self.bares_ordenados():
            coincide = texto in local.nombre.lower() or texto in local.codigo.lower()
            if self.estado.value == "cerrado":
                del_estado = self.vigilancia.cierre_activo(local.codigo) is not None
            else:
                del_estado = self.estado.value in ("todos", self.sensores.color_bar(local.codigo))
            if coincide and del_estado:
                tarjetas.append(self.tarjeta_bar(local))
        if not tarjetas:
            tarjetas.append(ft.Text("No hay ningún local que mostrar."))
        self.lista_bares.controls = tarjetas
        # Si viene de un evento (alguien ha escrito o elegido algo), refrescamos la pantalla.
        if evento:
            self.app.page.update()

    def seccion_bares(self):
        """Todos los bares de la zona con su semáforo, con buscador y filtro."""
        self.buscador = ft.TextField(label="Nombre o código", width=240, on_change=self.filtrar_bares)
        # Opciones del filtro: todos + los 3 colores + cerrados.
        opciones = {"todos": "Todos"}
        for color in COLORES:
            opciones[color] = SIGNIFICADO[color]
        opciones["cerrado"] = "Cerrados"
        self.estado = desplegable("Estado", opciones, "todos", self.filtrar_bares)
        self.lista_bares = ft.ResponsiveRow()
        self.filtrar_bares()
        return ft.Column(
            controls=[
                ft.Text("Bares de la zona", size=20, weight=ft.FontWeight.BOLD),
                ft.Row(wrap=True, controls=[self.buscador, self.estado]),
                self.lista_bares,
            ]
        )

    def seccion_notificaciones(self):
        """(Propietario y Autoridad) Avisos del usuario; los no leídos salen en negrita."""
        avisos = self.vigilancia.notificaciones_de(self.usuario)
        sin_leer = self.vigilancia.sin_leer(self.usuario)
        controles = []
        if not avisos:
            controles.append(ft.Text("No tienes notificaciones."))
        # avisos[:8] son los 8 primeros (los más nuevos).
        for aviso in avisos[:MAXIMO_AVISOS]:
            grosor = ft.FontWeight.NORMAL if aviso["leida"] else ft.FontWeight.BOLD
            controles.append(ft.Text(f"{aviso['fecha']} · {aviso['titulo']}", weight=grosor))
            controles.append(ft.Text(aviso["mensaje"], size=13))
        if sin_leer > 0:
            controles.append(ft.TextButton("Marcar como leídas", icon=ft.Icons.DONE_ALL, on_click=self.marcar_leidas))
        return seccion(f"Notificaciones ({sin_leer} sin leer)", controles, ft.Icons.NOTIFICATIONS)

    # ------------------------------------------------------------------
    # VECINO
    # ------------------------------------------------------------------
    def seccion_mi_calle(self):
        """Ruido y aforo de los bares de la calle del vecino."""
        calle = self.usuario.calle
        controles = [
            ft.TextButton("Cambiar mi calle", icon=ft.Icons.EDIT_LOCATION, on_click=self.pedir_calle),
        ]
        bares = self.locales.de_calle(calle)
        if not calle:
            controles.append(ft.Text("Todavía no has indicado tu calle."))
        elif not bares:
            controles.append(ft.Text("No hay locales registrados en tu calle."))
        for local in bares:
            tarjetas = []
            for tipo in TIPOS_VECINO:
                tarjetas.append(tarjeta_sensor(self.app, local.codigo, tipo))
            controles.append(ft.Text(f"{local.nombre} · {local.direccion}", size=16, weight=ft.FontWeight.BOLD))
            controles.append(estado_bar(self.app, local.codigo))
            controles.append(ft.ResponsiveRow(controls=tarjetas))
        return seccion(f"Mi calle: {calle or 'sin indicar'}", controles, ft.Icons.HOME)

    # ------------------------------------------------------------------
    # PROPIETARIO
    # ------------------------------------------------------------------
    def seccion_mi_local(self, local):
        """Estado del local, aforo y, si está cerrado, la opción de reclamar."""
        codigo = local.codigo
        personas = self.sensores.valor(codigo, "aforo")
        controles = [
            estado_bar(self.app, codigo),
            ft.Text(f"Aforo: {personas} de {local.aforo} personas"),
            # La barra se llena como máximo hasta 1 (aforo completo).
            ft.ProgressBar(value=min(1, personas / local.aforo), bar_height=12),
            fila_leds(self.app, codigo, 22),
            ft.TextButton(
                "Editar mi local", icon=ft.Icons.EDIT, on_click=lambda evento: self.app.ir_a_editar_local(local)
            ),
        ]
        cierre = self.vigilancia.cierre_activo(codigo)
        if cierre:
            controles.append(ft.Text(f"Cerrado el {cierre['fecha']} por {cierre['policia']}."))
            controles.append(ft.Text(f"Incidencia escrita por la policía: {cierre['motivo']}"))
            if cierre["estado_reclamacion"] == "":
                # Aún no ha reclamado: le damos la opción.
                controles.append(
                    ft.FilledButton(
                        "Presentar reclamación",
                        icon=ft.Icons.REPORT,
                        on_click=lambda evento: self.pedir_reclamacion(codigo),
                    )
                )
            else:
                controles.append(ft.Text(f"Tu reclamación: {cierre['reclamacion']}"))
                controles.append(ft.Text(f"Estado: {cierre['estado_reclamacion']}", weight=ft.FontWeight.BOLD))
                if cierre["respuesta"]:
                    controles.append(ft.Text(f"Respuesta de la policía: {cierre['respuesta']}"))
        # Si la última reclamación se resolvió a su favor, también se lo enseñamos.
        ultimo = self.vigilancia.ultimo_cierre(codigo)
        if not cierre and ultimo and ultimo["estado_reclamacion"] == "No justificado":
            controles.append(ft.Text(f"Tu última reclamación fue aceptada: {ultimo['respuesta']}"))
        return seccion(f"Mi local: {local.nombre}", controles, ft.Icons.STOREFRONT)

    def secciones_propietario(self):
        """Todo lo que ve el propietario de su local."""
        local = self.locales.buscar(self.usuario.codigo_negocio)
        if local is None:
            return [ft.Text("Tu local ya no está registrado. Contacta con la Autoridad.")]
        tarjetas = []
        for tipo in TIPOS_SENSOR:
            tarjetas.append(tarjeta_sensor(self.app, local.codigo, tipo))
        # El log incluye también sus cierres y reclamaciones anteriores.
        incidencias = self.vigilancia.incidencias_de(local.codigo)[:MAXIMO_INCIDENCIAS]
        return [
            self.seccion_mi_local(local),
            ft.ResponsiveRow(controls=tarjetas),
            seccion("Incidencias de mi local", [tabla_incidencias(self.app, incidencias)], ft.Icons.HISTORY),
        ]

    # ------------------------------------------------------------------
    # AUTORIDAD
    # ------------------------------------------------------------------
    def seccion_resumen(self):
        """Cuántos bares hay de cada color, cuántos cerrados y cuántas reclamaciones."""
        cuenta = {"verde": 0, "amarillo": 0, "rojo": 0}
        for local in self.locales.listar():
            color = self.sensores.color_bar(local.codigo)
            cuenta[color] = cuenta[color] + 1
        # (número, texto, icono) de cada casilla.
        casillas = []
        for color in COLORES:
            casillas.append((cuenta[color], SIGNIFICADO[color], icono_semaforo(color, 20)))
        casillas.append((len(self.vigilancia.cerrados()), "Cerrados", ft.Icon(ft.Icons.LOCK, size=20)))
        casillas.append(
            (len(self.vigilancia.reclamaciones_pendientes()), "Reclamaciones", ft.Icon(ft.Icons.GAVEL, size=20))
        )
        controles = []
        for numero, texto, icono in casillas:
            controles.append(
                ft.Column(
                    col={"xs": 6, "sm": 4, "md": 2},
                    controls=[
                        ft.Text(str(numero), size=28, weight=ft.FontWeight.BOLD),
                        ft.Row(wrap=True, spacing=4, controls=[icono, ft.Text(texto, size=12)]),
                    ],
                )
            )
        return seccion("Resumen de la zona", [ft.ResponsiveRow(controls=controles)], ft.Icons.DASHBOARD)

    def seccion_comparacion(self):
        """Gráfico que compara un sensor en todos los bares."""
        self.grafico = ft.Column()
        self.tipo = desplegable("Sensor", NOMBRE_SENSOR, TIPOS_SENSOR[0], self.comparar)
        self.comparar()
        return seccion("Comparación de bares", [self.tipo, self.grafico], ft.Icons.BAR_CHART)

    def comparar(self, evento=None):
        """Vuelve a dibujar el gráfico con el sensor elegido."""
        tipo = self.tipo.value
        filas = []
        for local in self.locales.listar():
            valor = self.sensores.valor(local.codigo, tipo)
            filas.append((local.nombre, valor, self.sensores.color_sensor(local.codigo, tipo, valor)))
        # De mayor a menor valor (fila[1] es el valor).
        filas.sort(key=lambda fila: fila[1], reverse=True)
        self.grafico.controls = [ft.Text(f"Valor actual en {UNIDAD_SENSOR[tipo]}", size=12), grafico_barras(filas)]
        if evento:
            self.app.page.update()

    def fila_alerta(self, local):
        """Una línea de alerta: bar en rojo + botón para cerrarlo."""
        return ft.Row(
            wrap=True,
            controls=[
                icono_semaforo("rojo"),
                ft.Text(f"{local.nombre} ({local.codigo})", weight=ft.FontWeight.BOLD),
                ft.Text(self.sensores.texto_valores(local.codigo)),
                ft.FilledButton(
                    "Cerrar temporalmente",
                    icon=ft.Icons.LOCK,
                    on_click=lambda evento: pedir_cierre(self.app, local),
                ),
            ],
        )

    def seccion_alertas(self):
        """Bares abiertos que están ahora mismo en ROJO."""
        controles = []
        for local in self.locales.listar():
            en_peligro = self.sensores.color_bar(local.codigo) == "rojo"
            if en_peligro and not self.vigilancia.cierre_activo(local.codigo):
                controles.append(self.fila_alerta(local))
        if not controles:
            controles.append(ft.Text("Ningún bar abierto tiene niveles peligrosos ahora mismo."))
        return seccion("Alertas de niveles peligrosos", controles, ft.Icons.WARNING)

    def fila_reclamacion(self, cierre):
        """Una reclamación con los dos botones para valorarla."""
        codigo = cierre["local"]
        return ft.Column(
            controls=[
                ft.Text(f"{self.locales.nombre_de(codigo)} ({codigo})", weight=ft.FontWeight.BOLD),
                ft.Text(f"Motivo del cierre ({cierre['policia']}): {cierre['motivo']}", size=13),
                ft.Text(f"Reclamación del propietario: {cierre['reclamacion']}", size=13),
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.OutlinedButton(
                            "Justificado (sigue cerrado)",
                            on_click=lambda evento: self.pedir_resolucion(codigo, True),
                        ),
                        ft.FilledButton(
                            "No justificado (reabrir)",
                            on_click=lambda evento: self.pedir_resolucion(codigo, False),
                        ),
                    ],
                ),
            ]
        )

    def seccion_reclamaciones(self):
        """Reclamaciones de propietarios que hay que valorar."""
        controles = []
        for cierre in self.vigilancia.reclamaciones_pendientes():
            controles.append(self.fila_reclamacion(cierre))
        if not controles:
            controles.append(ft.Text("No hay reclamaciones pendientes."))
        return seccion("Reclamaciones pendientes", controles, ft.Icons.GAVEL)

    def fila_cerrado(self, cierre):
        """Un bar cerrado con el botón para reabrirlo."""
        codigo = cierre["local"]
        return ft.Row(
            wrap=True,
            controls=[
                etiqueta_cerrado(),
                ft.Text(f"{self.locales.nombre_de(codigo)} ({codigo}) · desde {cierre['fecha']}"),
                ft.TextButton(
                    "Reabrir",
                    icon=ft.Icons.LOCK_OPEN,
                    on_click=lambda evento: pedir_reapertura(self.app, codigo),
                ),
            ],
        )

    def seccion_cerrados(self):
        """Bares cerrados ahora mismo, con el botón para reabrirlos."""
        controles = []
        for cierre in self.vigilancia.cerrados():
            controles.append(self.fila_cerrado(cierre))
        if not controles:
            controles.append(ft.Text("No hay bares cerrados."))
        return seccion("Bares cerrados temporalmente", controles, ft.Icons.LOCK)

    def seccion_incidencias(self):
        """Log de incidencias de toda la zona, con filtro por tipo."""
        opciones = {"": "Todas"}
        for tipo in TIPOS_INCIDENCIA:
            opciones[tipo] = tipo
        self.log = ft.Column()
        self.tipo_incidencia = desplegable("Tipo", opciones, "", self.filtrar_incidencias)
        self.filtrar_incidencias()
        return seccion("Incidencias de la zona", [self.tipo_incidencia, self.log], ft.Icons.HISTORY)

    def filtrar_incidencias(self, evento=None):
        """Vuelve a llenar el log con el tipo elegido."""
        incidencias = self.vigilancia.todas_las_incidencias(self.tipo_incidencia.value or "", MAXIMO_INCIDENCIAS)
        self.log.controls = [tabla_incidencias(self.app, incidencias)]
        if evento:
            self.app.page.update()

    # ------------------------------------------------------------------
    # ACCIONES DE LOS BOTONES
    # ------------------------------------------------------------------
    def marcar_leidas(self, evento):
        self.vigilancia.marcar_leidas(self.usuario)
        self.app.recargar()

    def pedir_calle(self, evento):
        """(Vecino) Pide el nombre de su calle."""
        ventana_texto(
            self.app,
            "Cambiar mi calle",
            "Escribe el nombre de tu calle, sin el número. Ejemplo: Calle Ferraz.",
            "Guardar",
            lambda calle: self.app.login_controller.users.cambiar_calle(self.usuario, calle),
        )

    def pedir_resolucion(self, codigo, justificado):
        """(Autoridad) Valora una reclamación con una respuesta para el propietario."""
        if justificado:
            titulo = "El cierre está justificado"
        else:
            titulo = "El cierre NO está justificado (se reabrirá el local)"
        ventana_texto(
            self.app,
            titulo,
            "Escribe la respuesta para el propietario.",
            "Enviar",
            lambda respuesta: self.vigilancia.resolver_reclamacion(self.usuario, codigo, justificado, respuesta),
        )

    def pedir_reclamacion(self, codigo):
        """(Propietario) Escribe una reclamación contra el cierre de su bar."""
        ventana_texto(
            self.app,
            "Presentar reclamación",
            "Explica por qué crees que el cierre no está justificado. La policía la valorará.",
            "Enviar reclamación",
            lambda texto: self.vigilancia.reclamar(self.usuario, codigo, texto),
        )

    # ------------------------------------------------------------------
    # PANTALLA COMPLETA
    # ------------------------------------------------------------------
    def construir(self):
        rol = self.usuario.rol
        botones = [
            ft.OutlinedButton("Cerrar sesión", on_click=self.app.ir_a_login),
            ft.FilledButton(TEXTO_BOTON_LOCALES[rol], icon=ft.Icons.STOREFRONT, on_click=self.app.ir_a_locales),
            ft.FilledButton("Actualizar medidas", icon=ft.Icons.REFRESH, on_click=self.app.medir_y_recargar),
        ]
        controles = [
            cabecera(self.app, f"¡Hola, {self.usuario.nombre}!", botones),
            ft.Text(DESCRIPCION_ROL[rol]),
        ]
        if rol == "Vecino":
            controles.append(self.seccion_mi_calle())
        if rol == "Propietario":
            controles.append(self.seccion_notificaciones())
            controles = controles + self.secciones_propietario()
        if rol == "Autoridad":
            controles = controles + [
                self.seccion_resumen(),
                self.seccion_alertas(),
                self.seccion_reclamaciones(),
                self.seccion_cerrados(),
                self.seccion_notificaciones(),
                self.seccion_comparacion(),
                self.seccion_incidencias(),
            ]
        controles.append(self.seccion_bares())
        return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=controles)
