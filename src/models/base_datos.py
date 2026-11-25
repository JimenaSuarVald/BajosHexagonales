"""MODELO: la BASE DE DATOS (SQLite) y las funciones para usarla.

Todos los datos de la aplicación están en un solo archivo: bajos_arguelles.db.
Este es el ÚNICO archivo del proyecto que abre la base de datos; el resto del
código pasa siempre por estas funciones:

    consultar(sql, datos)  -> lee y devuelve una lista enlazada de diccionarios
    ejecutar(sql, datos)   -> cambia algo (INSERT, UPDATE o DELETE)
    transaccion()          -> junta varios cambios: o se guardan todos o ninguno
    preparar()             -> crea la base de datos la primera vez

En las órdenes SQL los datos se ponen con "?" y se pasan aparte. Así, aunque
alguien escriba SQL en una caja de texto, se guarda como un texto normal.
"""
# "json", "os", "sqlite3", "threading" y "contextlib" vienen con Python.
import json
import os
import sqlite3
import threading
from contextlib import contextmanager

# Los datos leídos se manejan en memoria con una lista de nodos enlazados.
from src.models.lista_enlazada import ListaEnlazada

# Carpeta de este archivo (src/models): ahí están la base de datos y los JSON iniciales.
CARPETA = os.path.dirname(__file__)
NOMBRE_ARCHIVO = "bajos_arguelles.db"

# ----------------------------------------------------------------------
# MODELO RELACIONAL: las tablas, sus claves y sus índices.
#   PRIMARY KEY -> dato que identifica cada fila y no se repite.
#   REFERENCES  -> clave ajena: el valor tiene que existir en la otra tabla.
#   ON DELETE CASCADE -> si se borra el local, se borran también estas filas.
#   INDEX       -> como el índice de un libro: hace más rápidas las búsquedas.
#   NUMERIC     -> número; si no tiene decimales se guarda como entero (58 y no 58.0).
# ----------------------------------------------------------------------
ESQUEMA = """
CREATE TABLE locales (
    codigo     TEXT PRIMARY KEY,
    nombre     TEXT NOT NULL,
    direccion  TEXT NOT NULL,
    tipo       TEXT NOT NULL,
    aforo      INTEGER NOT NULL CHECK (aforo > 0)
);
CREATE TABLE ids_policiales (
    id TEXT PRIMARY KEY
);
CREATE TABLE usuarios (
    email          TEXT PRIMARY KEY,
    nombre         TEXT NOT NULL,
    rol            TEXT NOT NULL CHECK (rol IN ('Vecino', 'Propietario', 'Autoridad')),
    password_hash  TEXT NOT NULL,
    codigo_negocio TEXT UNIQUE REFERENCES locales (codigo) ON DELETE SET NULL,
    id_policial    TEXT UNIQUE REFERENCES ids_policiales (id),
    calle          TEXT NOT NULL DEFAULT ''
);
CREATE TABLE sensores (
    id    INTEGER PRIMARY KEY,
    local TEXT NOT NULL REFERENCES locales (codigo) ON DELETE CASCADE,
    tipo  TEXT NOT NULL,
    UNIQUE (local, tipo)
);
CREATE TABLE medidas (
    id     INTEGER PRIMARY KEY,
    sensor INTEGER NOT NULL REFERENCES sensores (id) ON DELETE CASCADE,
    valor  NUMERIC NOT NULL,
    fecha  TEXT NOT NULL
);
CREATE TABLE incidencias (
    id          INTEGER PRIMARY KEY,
    local       TEXT NOT NULL REFERENCES locales (codigo) ON DELETE CASCADE,
    fecha       TEXT NOT NULL,
    tipo        TEXT NOT NULL,
    autor       TEXT NOT NULL,
    descripcion TEXT NOT NULL
);
CREATE TABLE cierres (
    id                INTEGER PRIMARY KEY,
    local             TEXT NOT NULL REFERENCES locales (codigo) ON DELETE CASCADE,
    fecha             TEXT NOT NULL,
    policia           TEXT NOT NULL,
    motivo            TEXT NOT NULL,
    activo            INTEGER NOT NULL DEFAULT 1,
    reclamacion       TEXT NOT NULL DEFAULT '',
    estado_reclamacion TEXT NOT NULL DEFAULT '',
    respuesta         TEXT NOT NULL DEFAULT ''
);
CREATE TABLE notificaciones (
    id      INTEGER PRIMARY KEY,
    local   TEXT REFERENCES locales (codigo) ON DELETE CASCADE,
    fecha   TEXT NOT NULL,
    titulo  TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    leida   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX medidas_por_sensor ON medidas (sensor);
CREATE INDEX incidencias_por_local ON incidencias (local, tipo);
CREATE INDEX notificaciones_por_local ON notificaciones (local, leida);
CREATE UNIQUE INDEX un_cierre_activo ON cierres (local) WHERE activo = 1;
CREATE INDEX cierres_por_local ON cierres (local)
"""

# Guarda la transacción que está abierta (cada hilo del programa tiene la suya).
abierta = threading.local()


# ----------------------------------------------------------------------
# USAR LA BASE DE DATOS
# ----------------------------------------------------------------------
def conectar():
    """Abre la base de datos."""
    # timeout: si otro la está usando, espera hasta 10 segundos.
    # isolation_level=None: las transacciones las controlamos nosotros.
    conexion = sqlite3.connect(os.path.join(CARPETA, NOMBRE_ARCHIVO), timeout=10, isolation_level=None)
    # Para que cada fila se pueda convertir en diccionario.
    conexion.row_factory = sqlite3.Row
    # SQLite solo respeta las claves ajenas si se le pide.
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def transaccion():
    """Se usa con "with". Si algo falla dentro, se deshacen todos los cambios."""
    actual = getattr(abierta, "conexion", None)
    if actual is not None:
        # Ya hay una abierta: este cambio forma parte de ella.
        yield actual
        return
    conexion = conectar()
    try:
        conexion.execute("BEGIN IMMEDIATE")
        abierta.conexion = conexion
        yield conexion
        # Todo ha ido bien: se guarda.
        conexion.execute("COMMIT")
    except BaseException:
        # Algo ha fallado: se deshace.
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")
        raise
    finally:
        abierta.conexion = None
        conexion.close()


def ejecutar(sql, datos=()):
    """Cambia algo en la base de datos. Devuelve el id de la fila nueva (si es un INSERT)."""
    with transaccion() as conexion:
        return conexion.execute(sql, datos).lastrowid


def consultar(sql, datos=()):
    """Lee de la base de datos. Devuelve una lista enlazada de diccionarios."""
    # Dentro de una transacción hay que leer con su misma conexión.
    actual = getattr(abierta, "conexion", None)
    conexion = actual or conectar()
    try:
        resultado = ListaEnlazada()
        for fila in conexion.execute(sql, datos):
            resultado.append(dict(fila))
        return resultado
    finally:
        if actual is None:
            conexion.close()


def consultar_uno(sql, datos=()):
    """Como consultar(), pero devuelve solo la primera fila (o None si no hay)."""
    for fila in consultar(sql, datos):
        return fila
    return None


# ----------------------------------------------------------------------
# CREARLA LA PRIMERA VEZ
# ----------------------------------------------------------------------
def preparar():
    """Si la base de datos no existe, crea las tablas y mete los datos iniciales de los JSON."""
    # sqlite_master es una tabla propia de SQLite con la lista de tablas.
    if consultar_uno("SELECT name FROM sqlite_master WHERE name = 'medidas'"):
        return
    # Todo en una transacción: si un JSON está mal, no queda una base de datos a medias.
    with transaccion() as conexion:
        for orden in ESQUEMA.split(";"):
            conexion.execute(orden)
        importar_json()


def leer_json(nombre_archivo):
    """Devuelve la lista guardada en un archivo JSON (vacía si no existe)."""
    try:
        with open(os.path.join(CARPETA, nombre_archivo), encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return []


def insertar(tabla, fila):
    """Inserta un diccionario {columna: valor} en una tabla. Devuelve su id."""
    # Los nombres de tabla y columna los pone el programa, nunca el usuario.
    columnas = ", ".join(fila)
    huecos = ", ".join("?" * len(fila))
    return ejecutar(f"INSERT INTO {tabla} ({columnas}) VALUES ({huecos})", list(fila.values()))


def importar_json():
    """Pasa a la base de datos los datos que había en los archivos JSON."""
    # Si aún no hay locales.json, se usa el de ejemplo (el Bar Demo).
    for local in leer_json("locales.json") or leer_json("locales.example.json"):
        insertar("locales", local)
    for id_policial in leer_json("ids_policiales.json"):
        insertar("ids_policiales", {"id": id_policial})

    # Códigos que existen: lo que apunte a un local que ya no existe no se importa.
    codigos = [fila["codigo"] for fila in consultar("SELECT codigo FROM locales")]
    ids = [fila["id"] for fila in consultar("SELECT id FROM ids_policiales")]

    for usuario in leer_json("usuarios.json"):
        # En la base de datos, "no tiene" se guarda como NULL (None) y no como "".
        if usuario.get("codigo_negocio") not in codigos:
            usuario["codigo_negocio"] = None
        if usuario.get("id_policial") not in ids:
            usuario["id_policial"] = None
        insertar("usuarios", usuario)

    # Cada sensor y todas sus medidas (el historial previo).
    historial = leer_json("historial_sensores.json")
    for sensor in leer_json("sensores.json"):
        if sensor["local"] not in codigos:
            continue
        id_sensor = insertar("sensores", {"local": sensor["local"], "tipo": sensor["tipo"]})
        ultima = None
        for medida in historial:
            if medida["local"] == sensor["local"] and medida["tipo"] == sensor["tipo"]:
                insertar("medidas", {"sensor": id_sensor, "valor": medida["valor"], "fecha": medida["fecha"]})
                ultima = medida
        # Si el valor actual no estaba en el historial, se añade al final.
        if ultima is None or (ultima["valor"], ultima["fecha"]) != (sensor["valor"], sensor["fecha"]):
            insertar("medidas", {"sensor": id_sensor, "valor": sensor["valor"], "fecha": sensor["fecha"]})

    for tabla in ("incidencias", "cierres"):
        for fila in leer_json(tabla + ".json"):
            if fila["local"] in codigos:
                insertar(tabla, fila)
    for aviso in leer_json("notificaciones.json"):
        # local = NULL significa que el aviso es para la Autoridad.
        para = aviso.pop("para")
        if para in codigos or para == "Autoridad":
            aviso["local"] = None if para == "Autoridad" else para
            insertar("notificaciones", aviso)
