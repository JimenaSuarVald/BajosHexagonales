"""MODELO: datos de VIGILANCIA (incidencias, cierres y notificaciones).

Son tres tablas de la base de datos (ver ESQUEMA en base_datos.py):

    incidencias    -> el LOG (registro) de incidencias de cada bar
    cierres        -> los cierres temporales que ha hecho la policía
                      activo: 1 mientras el local siga cerrado
                      estado_reclamacion: "", "Pendiente", "Justificado" o "No justificado"
    notificaciones -> avisos que ve cada usuario en su panel
                      local: el código del local (lo ve su propietario) o NULL
                      (lo ven todos los policías)
"""
from src.models.base_datos import consultar, consultar_uno, ejecutar, insertar


# ----------------------------------------------------------------------
# INCIDENCIAS
# ----------------------------------------------------------------------
def guardar_incidencia(codigo, fecha, tipo, autor, descripcion):
    insertar(
        "incidencias",
        {"local": codigo, "fecha": fecha, "tipo": tipo, "autor": autor, "descripcion": descripcion},
    )


def incidencias_de(codigo):
    """Las de un local, de la más nueva a la más antigua."""
    return consultar("SELECT * FROM incidencias WHERE local = ? ORDER BY id DESC", (codigo,))


def ultimas_incidencias(tipo, cantidad):
    """Las últimas de todos los locales. tipo="" significa todos los tipos."""
    return consultar(
        "SELECT * FROM incidencias WHERE ? IN ('', tipo) ORDER BY id DESC LIMIT ?", (tipo, cantidad)
    )


# ----------------------------------------------------------------------
# CIERRES
# ----------------------------------------------------------------------
def guardar_cierre(codigo, fecha, policia, motivo):
    insertar("cierres", {"local": codigo, "fecha": fecha, "policia": policia, "motivo": motivo})


def cierre_activo(codigo):
    """El cierre que tiene ahora el local, o None si está abierto."""
    return consultar_uno("SELECT * FROM cierres WHERE local = ? AND activo = 1", (codigo,))


def ultimo_cierre(codigo):
    """El último cierre del local (activo o no), o None si nunca lo han cerrado."""
    return consultar_uno("SELECT * FROM cierres WHERE local = ? ORDER BY id DESC LIMIT 1", (codigo,))


def cierres_activos():
    return consultar("SELECT * FROM cierres WHERE activo = 1 ORDER BY id")


def cierres_con_reclamacion_pendiente(codigo=""):
    """Los de un local, o los de todos si codigo=""."""
    return consultar(
        "SELECT * FROM cierres WHERE estado_reclamacion = 'Pendiente' AND ? IN ('', local) ORDER BY id", (codigo,)
    )


def actualizar_cierre(cierre):
    """Guarda los cambios hechos en un cierre."""
    ejecutar(
        "UPDATE cierres SET activo = ?, reclamacion = ?, estado_reclamacion = ?, respuesta = ? WHERE id = ?",
        (
            cierre["activo"], cierre["reclamacion"], cierre["estado_reclamacion"], cierre["respuesta"], cierre["id"],
        ),
    )


# ----------------------------------------------------------------------
# NOTIFICACIONES (codigo=None son las de la Autoridad; "IS" también sirve para comparar con NULL)
# ----------------------------------------------------------------------
def guardar_notificacion(codigo, fecha, titulo, mensaje):
    insertar("notificaciones", {"local": codigo, "fecha": fecha, "titulo": titulo, "mensaje": mensaje})


def notificaciones_de(codigo):
    """De la más nueva a la más antigua."""
    return consultar("SELECT * FROM notificaciones WHERE local IS ? ORDER BY id DESC", (codigo,))


def marcar_leidas(codigo):
    ejecutar("UPDATE notificaciones SET leida = 1 WHERE local IS ?", (codigo,))
