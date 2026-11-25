"""CONTROLADOR de la aplicación: decide qué pantalla se ve en cada momento."""
# Flet es la librería que dibuja la interfaz gráfica (ventanas, botones, textos...).
import flet as ft

# Controladores: contienen la lógica (comprobar datos, guardar, permisos...).
from src.controllers.local_controller import LocalController
from src.controllers.login_controller import LoginController
from src.controllers.sensor_controller import SensorController
from src.controllers.vigilancia_controller import VigilanciaController

# La base de datos.
from src.models.base_datos import preparar

# Vistas: cada una dibuja una pantalla.
from src.views.bar_sensores_view import BarSensoresView
from src.views.local_form_view import LocalFormView
from src.views.locales_view import LocalesView
from src.views.login_view import LoginView
from src.views.panel_sensores_view import PanelSensoresView
from src.views.register_view import RegisterView


class App:
    def __init__(self, page):
        # "page" es la ventana de la aplicación; la guardamos para usarla después.
        self.page = page
        # Texto que aparece en la barra de título de la ventana.
        self.page.title = "Bajos de Argüelles · Monitorización ambiental"
        # Tema claro (fondo blanco).
        self.page.theme_mode = ft.ThemeMode.LIGHT
        # La primera vez se crea la base de datos con los datos iniciales.
        preparar()
        # Creamos los controladores una sola vez y los compartimos con las vistas.
        self.login_controller = LoginController()
        self.local_controller = LocalController()
        self.sensor_controller = SensorController()
        self.vigilancia_controller = VigilanciaController()
        # Usuario que ha iniciado sesión. None significa "nadie".
        self.usuario = None
        # Función que vuelve a dibujar la pantalla que se está viendo (ver recargar()).
        self.pantalla_actual = self.ir_a_login

    def mostrar(self, pantalla):
        """Quita lo que hay en la ventana y pone la pantalla indicada."""
        # Borra todo lo que se ve ahora.
        self.page.clean()
        # Añade la pantalla nueva.
        self.page.add(pantalla)

    def recargar(self):
        """Vuelve a dibujar la pantalla actual (después de un cambio)."""
        self.pantalla_actual()

    def medir(self):
        """Toma medidas nuevas en todos los bares y revisa si hay que avisar a la policía."""
        self.sensor_controller.medir_todos()
        self.vigilancia_controller.revisar_alertas(self.sensor_controller)

    def medir_y_recargar(self, evento=None):
        """Botón "Actualizar medidas"."""
        self.medir()
        self.recargar()

    # "evento=None" permite llamar a estas funciones desde un botón (que manda
    # un evento) o directamente desde el código (sin mandar nada).

    def ir_a_login(self, evento=None):
        # Al volver al login se cierra la sesión.
        self.usuario = None
        self.mostrar(LoginView(self).construir())

    def ir_a_registro(self, evento=None):
        self.mostrar(RegisterView(self).construir())

    def entrar(self, usuario):
        """Se llama cuando el login o el registro han ido bien."""
        # Recordamos quién ha entrado.
        self.usuario = usuario
        # Tomamos medidas nuevas para que el panel esté al día.
        self.medir()
        # Y lo llevamos a la pantalla principal.
        self.ir_a_principal()

    def ir_a_principal(self, evento=None):
        self.pantalla_actual = self.ir_a_principal
        self.mostrar(PanelSensoresView(self).construir())

    def ir_a_locales(self, evento=None):
        self.pantalla_actual = self.ir_a_locales
        self.mostrar(LocalesView(self).construir())

    def ir_a_bar(self, local):
        # Permiso: la Autoridad, o el Propietario de ese local.
        if not self.local_controller.puede_ver_sensores(self.usuario, local):
            return
        # "lambda: self.ir_a_bar(local)" guarda cómo volver a ESTE mismo bar.
        self.pantalla_actual = lambda: self.ir_a_bar(local)
        self.mostrar(BarSensoresView(self, local).construir())

    def ir_a_nuevo_local(self, evento=None):
        # Sin local: el formulario sale vacío para crear uno nuevo.
        self.mostrar(LocalFormView(self).construir())

    def ir_a_editar_local(self, local):
        # Con local: el formulario sale relleno con sus datos para editarlos.
        self.mostrar(LocalFormView(self, local).construir())
