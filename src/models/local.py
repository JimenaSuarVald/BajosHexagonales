"""MODELO: define qué es un local (bar, restaurante...) y cómo se guarda en la base de datos (tabla locales)."""
# "re" busca patrones en textos y "unicodedata" permite quitar las tildes. Vienen con Python.
import re
import unicodedata

# Traemos las funciones de la base de datos (ver base_datos.py).
from src.models.base_datos import consultar, consultar_uno, ejecutar, insertar
from src.models.lista_enlazada import ListaEnlazada

# Tipos de local que se pueden elegir en el formulario.
TIPOS_LOCAL = ["Bar", "Restaurante", "Discoteca", "Otro"]


# Molde que describe los datos de cada local.
class Local:
    # Se ejecuta al crear un local nuevo y guarda sus datos.
    def __init__(self, codigo, nombre, direccion, tipo, aforo):
        # Código de negocio: identifica al local y no se repite (ejemplo "NEG-001").
        # El propietario lo necesita para registrarse.
        self.codigo = codigo
        # Nombre comercial del local.
        self.nombre = nombre
        # Calle y número.
        self.direccion = direccion
        # Uno de los TIPOS_LOCAL de arriba.
        self.tipo = tipo
        # Número máximo de personas permitidas dentro (un número entero).
        self.aforo = aforo

    def esta_en(self, calle):
        """True si el local está en esa calle (no importan mayúsculas, tildes ni "Calle" o "C/")."""
        return bool(calle) and simplificar_calle(self.direccion) == simplificar_calle(calle)


def simplificar_calle(texto):
    """Deja solo el nombre de la calle: "C/ Martín de los Heros, nº 3" -> "martin de los heros"."""
    # NFD separa cada letra de su tilde; "Mn" son las tildes, que no copiamos.
    sin_tildes = ""
    for letra in unicodedata.normalize("NFD", texto.lower().strip()):
        if unicodedata.category(letra) != "Mn":
            sin_tildes = sin_tildes + letra
    # Quita "calle", "c/" o "c." del principio.
    nombre = re.sub(r"^(calle\b|c/|c\.)\s*", "", sin_tildes)
    # Quita el número del portal y lo que venga detrás (", nº 3", " 10", " 10 bajo B").
    nombre = re.sub(r"[\s,]+(n[ºo°.]*\s*)?\d.*$", "", nombre)
    return nombre.strip(" ,.")


def crear_desde_fila(fila):
    """Convierte una fila de la tabla en un objeto Local."""
    return Local(fila["codigo"], fila["nombre"], fila["direccion"], fila["tipo"], fila["aforo"])


def cargar_locales():
    """Devuelve la lista de todos los locales."""
    locales = ListaEnlazada()
    for fila in consultar("SELECT * FROM locales ORDER BY rowid"):
        locales.append(crear_desde_fila(fila))
    return locales


def buscar_local(codigo):
    """El local con ese código, o None si no existe."""
    fila = consultar_uno("SELECT * FROM locales WHERE codigo = ?", (codigo,))
    if fila is None:
        return None
    return crear_desde_fila(fila)


def insertar_local(local):
    """Guarda un local nuevo. vars() da sus datos como diccionario."""
    insertar("locales", vars(local))


def actualizar_local(local):
    """Guarda los cambios de un local."""
    ejecutar(
        "UPDATE locales SET nombre = ?, direccion = ?, tipo = ?, aforo = ? WHERE codigo = ?",
        (local.nombre, local.direccion, local.tipo, local.aforo, local.codigo),
    )


def borrar_local(codigo):
    """Borra un local. Por ON DELETE CASCADE se borran también sus datos en las demás tablas."""
    ejecutar("DELETE FROM locales WHERE codigo = ?", (codigo,))
