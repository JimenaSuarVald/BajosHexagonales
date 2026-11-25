"""CONTROLADOR de usuarios: los crea, los busca y protege sus contraseñas."""
# hashlib es una herramienta de Python para transformar textos de forma irreversible.
import hashlib

# Traemos del modelo el molde Usuario y las funciones que leen/escriben en la base de datos.
from src.models.usuario import (
    Usuario,
    actualizar_calle,
    buscar_usuario,
    cargar_usuarios,
    existe_id_policial,
    insertar_usuario,
)


class UserController:
    def __init__(self):
        # La primera vez que se abre la aplicación (no hay usuarios) crea uno por rol.
        if not cargar_usuarios():
            # Vecino: vive en la misma calle que el local de prueba.
            self.crear_usuario("Vecino Demo", "vecino@arguelles.es", "1234", "Vecino", calle="Calle Ferraz")
            # Propietario: va unido al local de prueba "NEG-001".
            self.crear_usuario(
                "Bar Demo", "bar@arguelles.es", "1234", "Propietario", codigo_negocio="NEG-001"
            )
            # Autoridad: usa el ID policial de prueba "POL-0001".
            self.crear_usuario(
                "Ayuntamiento Demo", "ayto@arguelles.es", "1234", "Autoridad", id_policial="POL-0001"
            )

    def calcular_hash(self, password):
        """Transforma la contraseña para no guardarla tal cual."""
        # encode convierte el texto en bytes; sha256 lo transforma;
        # hexdigest lo devuelve como un texto de 64 letras y números.
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def password_correcta(self, usuario, password):
        """Devuelve True si la contraseña escrita coincide con la guardada."""
        # Transformamos la contraseña escrita y la comparamos con la guardada.
        return usuario.password_hash == self.calcular_hash(password)

    def buscar_por_email(self, email):
        """Devuelve el usuario con ese correo, o None si no existe."""
        return buscar_usuario("email", email)

    def buscar_por_codigo_negocio(self, codigo):
        """Devuelve el propietario que tiene ese código de negocio, o None."""
        return buscar_usuario("codigo_negocio", codigo)

    def buscar_por_id_policial(self, id_policial):
        """Devuelve la autoridad que tiene ese ID policial, o None."""
        return buscar_usuario("id_policial", id_policial)

    def id_policial_valido(self, id_policial):
        """Devuelve True si el ID está en la lista oficial."""
        return existe_id_policial(id_policial)

    def crear_usuario(self, nombre, email, password, rol, codigo_negocio="", id_policial="", calle=""):
        """Crea un usuario, lo guarda y lo devuelve."""
        # Creamos el usuario guardando la contraseña ya transformada.
        usuario = Usuario(
            nombre, email, rol, self.calcular_hash(password), codigo_negocio, id_policial, calle
        )
        # Lo guardamos en la base de datos.
        insertar_usuario(usuario)
        # Devolvemos el usuario recién creado.
        return usuario

    def cambiar_calle(self, usuario, calle):
        """Un vecino cambia su calle. Devuelve "" si ha ido bien o el error."""
        if usuario.rol != "Vecino":
            return "Solo los vecinos tienen calle."
        calle = calle.strip()
        if not calle:
            return "Escribe el nombre de tu calle."
        actualizar_calle(usuario.email, calle)
        # También en el usuario que está conectado ahora.
        usuario.calle = calle
        return ""
