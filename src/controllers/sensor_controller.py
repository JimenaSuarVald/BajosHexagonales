"""CONTROLADOR de sensores: crea los sensores de cada bar, toma medidas y
decide el color de cada bar (semáforo), los LEDs y el ventilador.

REGLAS (los números están en UMBRALES, en models/sensor.py)
    Semáforo de cada sensor:
        verde    -> todo bien
        amarillo -> precaución (se acerca al límite)
        rojo     -> PELIGRO
    Semáforo del bar = el peor color de sus sensores.

    LED ROJO   -> temperatura en peligro.
    LED AZUL   -> humedad en peligro.
    LED VERDE  -> calidad del aire en peligro ("Mala").
    VENTILADOR -> se enciende si la temperatura Y el aire están en peligro a la vez.
"""
# "datetime" da la fecha y hora; "timedelta" sirve para restar horas.
from datetime import datetime, timedelta

# La base de datos y los locales que ya existen (del CRUD de locales).
from src.models.base_datos import transaccion
from src.models.local import buscar_local, cargar_locales

# Datos y umbrales de los sensores.
from src.models.sensor import (
    CALIDAD_AIRE,
    LED_SENSOR,
    NOMBRE_SENSOR,
    TIPOS_SENSOR,
    UMBRALES,
    UNIDAD_SENSOR,
    historial_de,
    insertar_medida,
    insertar_sensor,
    sensores_actuales,
)

# El simulador que se inventa las medidas.
from src.models.simulador_sensores import siguiente_valor, valor_al_azar

# Colores del semáforo, del mejor al peor (la posición sirve para compararlos).
COLORES = ["verde", "amarillo", "rojo"]


def fecha_actual():
    """Fecha y hora de ahora como texto. Ejemplo: "2026-11-13 21:30"."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def crear_historial(local, tipo, id_sensor):
    """Inventa una medida por hora de las últimas 24 horas de un sensor.

    Entre las 23:00 y la 01:59 el bar está lleno, así que esas horas se
    inventan con el escenario "alerta" (y salen alertas en el historial).
    """
    ahora = datetime.now()
    # range(24, -1, -1) cuenta hacia atrás: 24, 23, 22, ... 1, 0 (horas atrás).
    for horas_atras in range(24, -1, -1):
        momento = ahora - timedelta(hours=horas_atras)
        if momento.hour >= 23 or momento.hour <= 1:
            escenario = "alerta"
        else:
            escenario = "normal"
        valor = valor_al_azar(tipo, escenario, local.aforo)
        insertar_medida(id_sensor, valor, momento.strftime("%Y-%m-%d %H:%M"))


def preparar_sensores():
    """Da a cada bar los sensores que le falten (con su historial).

    Se usa al arrancar, al crear un local y antes de cada medida.
    """
    # Sensores que ya existen. Ejemplo: [("NEG-001", "ruido"), ...].
    existentes = []
    for sensor in sensores_actuales():
        existentes.append((sensor["local"], sensor["tipo"]))
    # Todo en una transacción: no puede quedar un sensor sin medidas.
    with transaccion():
        for local in cargar_locales():
            for tipo in TIPOS_SENSOR:
                if (local.codigo, tipo) not in existentes:
                    crear_historial(local, tipo, insertar_sensor(local.codigo, tipo))


class SensorController:
    def __init__(self):
        # Escenario de cada bar: "normal" o "alerta". Ejemplo: {"NEG-001": "alerta"}.
        # Si un bar no aparece aquí, está en "normal".
        self.escenarios = {}
        # Nos aseguramos de que todos los bares tienen sus sensores.
        preparar_sensores()

    # ------------------------------------------------------------------
    # CONSULTAR
    # ------------------------------------------------------------------
    def sensores_de(self, codigo):
        """Los sensores de un bar."""
        return sensores_actuales(codigo)

    def valor(self, codigo, tipo):
        """El último valor de un sensor concreto de un bar (0 si no existe)."""
        sensor = self.sensores_de(codigo).buscar(lambda sensor: sensor["tipo"] == tipo)
        if sensor is None:
            return 0
        return sensor["valor"]

    def historial_de(self, codigo, tipo, cantidad):
        """Las últimas "cantidad" medidas de un sensor, de la más nueva a la más antigua."""
        # list() la pasa a lista normal, que es lo que usan los gráficos.
        return list(historial_de(codigo, tipo, cantidad))

    def estadisticas(self, medidas):
        """Mínimo, media y máximo de unas medidas (None si no hay ninguna)."""
        if not medidas:
            return None
        valores = []
        for medida in medidas:
            valores.append(medida["valor"])
        return min(valores), round(sum(valores) / len(valores), 1), max(valores)

    def texto_valores(self, codigo, tipos=TIPOS_SENSOR):
        """Los valores actuales en una línea. Ejemplo: "Temperatura: 23.4 °C · Humedad: 50 %"."""
        partes = []
        for tipo in tipos:
            partes.append(f"{NOMBRE_SENSOR[tipo]}: {self.valor(codigo, tipo)} {UNIDAD_SENSOR[tipo]}")
        return " · ".join(partes)

    # ------------------------------------------------------------------
    # REGLAS (semáforo, LEDs y ventilador)
    # ------------------------------------------------------------------
    def limites(self, codigo, tipo):
        """Los umbrales de un sensor. Los del aforo se pasan de % a personas de ESE local."""
        umbrales = UMBRALES[tipo]
        if tipo != "aforo":
            return umbrales
        local = buscar_local(codigo)
        resultado = {}
        for nombre in umbrales:
            # Si el local ya no existe contamos 100 personas.
            resultado[nombre] = umbrales[nombre] * (local.aforo if local else 100) / 100
        return resultado

    def color_sensor(self, codigo, tipo, valor):
        """Semáforo de UN sensor: "verde", "amarillo" o "rojo"."""
        limites = self.limites(codigo, tipo)
        # limites.get("x", valor) devuelve el propio valor si ese límite no existe:
        # así la comparación sale False y no cuenta.
        if valor > limites["peligro"] or valor < limites.get("peligro_minimo", valor):
            return "rojo"
        if valor > limites["precaucion"] or valor < limites.get("precaucion_minima", valor):
            return "amarillo"
        return "verde"

    def calidad_aire(self, ppm):
        """Convierte los ppm de CO2 en "Buena", "Moderada" o "Mala"."""
        return CALIDAD_AIRE[self.color_sensor("", "calidad_aire", ppm)]

    def color_bar(self, codigo):
        """Semáforo del BAR: el peor color de sus sensores."""
        peor = "verde"
        for sensor in self.sensores_de(codigo):
            color = self.color_sensor(codigo, sensor["tipo"], sensor["valor"])
            # index() da la posición en COLORES: cuanto mayor, peor.
            if COLORES.index(color) > COLORES.index(peor):
                peor = color
        return peor

    def leds(self, codigo):
        """Qué LEDs están encendidos en un bar. Ejemplo: {"rojo": True, "azul": False, "verde": True}."""
        encendidos = {"rojo": False, "azul": False, "verde": False}
        for sensor in self.sensores_de(codigo):
            tipo = sensor["tipo"]
            # Cada sensor enciende su LED (temperatura -> rojo, etc.).
            if tipo in LED_SENSOR and self.color_sensor(codigo, tipo, sensor["valor"]) == "rojo":
                encendidos[LED_SENSOR[tipo]] = True
        return encendidos

    def ventilador(self, codigo):
        """True si el ventilador del bar debe estar encendido: calor Y aire malo a la vez."""
        leds = self.leds(codigo)
        return leds[LED_SENSOR["temperatura"]] and leds[LED_SENSOR["calidad_aire"]]

    # ------------------------------------------------------------------
    # SIMULAR MEDIDAS
    # ------------------------------------------------------------------
    def puede_simular(self, usuario):
        """Solo la Autoridad puede usar el simulador de pruebas."""
        return usuario.rol == "Autoridad"

    def escenario(self, codigo):
        """Escenario del bar: "alerta" si se ha forzado, si no "normal"."""
        return self.escenarios.get(codigo, "normal")

    def simular(self, usuario, codigo, escenario):
        """Cambia el escenario de un bar: sus próximas medidas irán hacia esos valores."""
        if not self.puede_simular(usuario):
            return "Solo la Autoridad puede usar el simulador."
        self.escenarios[codigo] = escenario
        return ""

    def medir_todos(self):
        """Toma una medida nueva de TODOS los sensores de TODOS los bares."""
        preparar_sensores()
        # Aforo máximo de cada local. Ejemplo: {"NEG-001": 80}.
        aforos = {}
        for local in cargar_locales():
            aforos[local.codigo] = local.aforo

        fecha = fecha_actual()
        # Una sola transacción para todas las medidas: es mucho más rápido.
        with transaccion():
            for sensor in sensores_actuales():
                codigo = sensor["local"]
                valor = siguiente_valor(sensor["tipo"], sensor["valor"], self.escenario(codigo), aforos[codigo])
                insertar_medida(sensor["id"], valor, fecha)
