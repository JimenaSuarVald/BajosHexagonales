"""VISTA: detalle de UN bar: sus sensores, LEDs, ventilador, historial y log de incidencias.

Solo la ven la Autoridad y el Propietario de ese bar (lo comprueba App.ir_a_bar).
La Autoridad tiene además los botones de cerrar o reabrir el bar y un pequeño
"simulador" para pruebas que permite forzar valores peligrosos.
"""
# Flet es la librería que dibuja la interfaz gráfica.
import flet as ft

# Los tipos de sensor.
from src.models.sensor import TIPOS_SENSOR

# Piezas que se repiten en varias pantallas.
from src.views.piezas_sensores import (
    cabecera,
    estado_bar,
    fila_leds,
    pedir_cierre,
    pedir_reapertura,
    seccion,
    tabla_incidencias,
    tarjeta_sensor,
)


class BarSensoresView:
    def __init__(self, app, local):
        self.app = app
        # El bar que estamos viendo.
        self.local = local
        self.codigo = local.codigo
        self.sensores = app.sensor_controller
        self.vigilancia = app.vigilancia_controller

    def boton_policia(self):
        """(Autoridad) Botón para cerrar o reabrir este bar."""
        if self.vigilancia.cierre_activo(self.codigo):
            return ft.OutlinedButton(
                "Reabrir local",
                icon=ft.Icons.LOCK_OPEN,
                on_click=lambda evento: pedir_reapertura(self.app, self.codigo),
            )
        return ft.FilledButton(
            "Cerrar temporalmente", icon=ft.Icons.LOCK, on_click=lambda evento: pedir_cierre(self.app, self.local)
        )

    def simulador(self):
        """(Autoridad) Botones de prueba para cambiar las medidas de este bar."""
        if self.sensores.escenario(self.codigo) == "alerta":
            situacion = "Ahora se simula: situación de ALERTA."
        else:
            situacion = "Ahora se simula: situación normal."
        controles = [
            ft.Text(situacion, italic=True),
            ft.Row(
                wrap=True,
                controls=[
                    ft.OutlinedButton(
                        "Forzar alerta", icon=ft.Icons.WARNING, on_click=lambda evento: self.simular("alerta")
                    ),
                    ft.OutlinedButton(
                        "Volver a normal", icon=ft.Icons.CHECK_CIRCLE, on_click=lambda evento: self.simular("normal")
                    ),
                ],
            ),
            ft.Text(
                "Los valores cambian poco a poco: pulsa \"Actualizar medidas\" "
                "varias veces para ver cómo suben o bajan.",
                size=12,
            ),
        ]
        return seccion("Simulador (solo para pruebas)", controles, ft.Icons.SCIENCE)

    def simular(self, escenario):
        """Cambia el escenario y toma medidas nuevas."""
        self.sensores.simular(self.app.usuario, self.codigo, escenario)
        self.app.medir_y_recargar()

    def construir(self):
        es_autoridad = self.app.usuario.rol == "Autoridad"
        botones = [
            ft.OutlinedButton("Volver", icon=ft.Icons.ARROW_BACK, on_click=self.app.ir_a_principal),
            ft.FilledButton("Actualizar medidas", icon=ft.Icons.REFRESH, on_click=self.app.medir_y_recargar),
        ]
        if es_autoridad:
            botones.append(self.boton_policia())

        tarjetas = []
        for tipo in TIPOS_SENSOR:
            tarjetas.append(tarjeta_sensor(self.app, self.codigo, tipo, con_tabla=True))

        incidencias = tabla_incidencias(self.app, self.vigilancia.incidencias_de(self.codigo))
        controles = [
            cabecera(self.app, self.local.nombre, botones),
            ft.Text(f"{self.codigo} · {self.local.tipo} · {self.local.direccion}"),
            estado_bar(self.app, self.codigo),
            seccion("Alertas (LEDs) y ventilador", [fila_leds(self.app, self.codigo, 30)], ft.Icons.LIGHTBULB),
            ft.ResponsiveRow(controls=tarjetas),
            seccion("Log de incidencias", [incidencias], ft.Icons.HISTORY),
        ]
        if self.sensores.puede_simular(self.app.usuario):
            controles.append(self.simulador())
        return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=controles)
