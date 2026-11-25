"""MODELO: define qué es un usuario y cómo se guarda en la base de datos (tabla usuarios)."""
# Traemos las funciones de la base de datos (ver base_datos.py).
from src.models.base_datos import consultar, consultar_uno, ejecutar, insertar
from src.models.lista_enlazada import ListaEnlazada

# Los tres tipos de usuario (roles) que existen. Están explicados en docs/ROLES.md.
ROLES = ["Vecino", "Propietario", "Autoridad"]


# Una "clase" es un molde: describe qué datos tiene cada usuario.
class Usuario:
    # __init__ se ejecuta al crear un usuario nuevo y guarda sus datos.
    # codigo_negocio, id_policial y calle valen "" (vacío) si no se indican.
    def __init__(self, nombre, email, rol, password_hash, codigo_negocio="", id_policial="", calle=""):
        # Nombre que se muestra en pantalla.
        self.nombre = nombre
        # Correo electrónico; sirve para iniciar sesión y no se puede repetir.
        self.email = email
        # Rol del usuario: "Vecino", "Propietario" o "Autoridad".
        self.rol = rol
        # Contraseña ya transformada (hash). Nunca guardamos la contraseña real.
        self.password_hash = password_hash
        # Solo Propietarios: código del local que les pertenece (ejemplo "NEG-001").
        self.codigo_negocio = codigo_negocio
        # Solo Autoridad: su ID de identificación policial (ejemplo "POL-0001").
        self.id_policial = id_policial
        # Solo Vecinos: calle donde vive (ejemplo "Calle Ferraz").
        self.calle = calle


def crear_desde_fila(fila):
    """Convierte una fila de la tabla en un objeto Usuario."""
    # En la base de datos "no tiene" es NULL (None); en el programa usamos "".
    return Usuario(
        fila["nombre"],
        fila["email"],
        fila["rol"],
        fila["password_hash"],
        fila["codigo_negocio"] or "",
        fila["id_policial"] or "",
        fila["calle"],
    )


def cargar_usuarios():
    """Devuelve la lista de todos los usuarios."""
    usuarios = ListaEnlazada()
    for fila in consultar("SELECT * FROM usuarios ORDER BY rowid"):
        usuarios.append(crear_desde_fila(fila))
    return usuarios


def buscar_usuario(columna, valor):
    """El usuario que tiene ese valor en esa columna ("email", "codigo_negocio"...), o None."""
    fila = consultar_uno(f"SELECT * FROM usuarios WHERE {columna} = ?", (valor,))
    if fila is None:
        return None
    return crear_desde_fila(fila)


def insertar_usuario(usuario):
    """Guarda un usuario nuevo."""
    insertar(
        "usuarios",
        {
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "password_hash": usuario.password_hash,
            # "or None": si está vacío se guarda como NULL.
            "codigo_negocio": usuario.codigo_negocio or None,
            "id_policial": usuario.id_policial or None,
            "calle": usuario.calle,
        },
    )


def actualizar_calle(email, calle):
    """Cambia la calle de un usuario."""
    ejecutar("UPDATE usuarios SET calle = ? WHERE email = ?", (calle, email))


def existe_id_policial(id_policial):
    """True si el ID está en la lista oficial (tabla ids_policiales)."""
    return consultar_uno("SELECT id FROM ids_policiales WHERE id = ?", (id_policial,)) is not None
