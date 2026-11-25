"""MODELO: datos de los SENSORES y su HISTORIAL.

Cada local (bar) tiene 5 sensores. Son dos tablas de la base de datos:

    sensores -> qué sensores tiene cada local (local y tipo)
    medidas  -> TODAS las medidas de cada sensor (valor y fecha). La última es su valor actual.
"""
# Las funciones de la base de datos que usa todo el proyecto.
from src.models.base_datos import consultar, insertar

# Los tipos de sensor. Para añadir otro: ponerlo aquí, en las tablas de abajo,
# en RANGOS (simulador_sensores.py) y en ICONO_SENSOR (piezas_sensores.py).
TIPOS_SENSOR = ["temperatura", "humedad", "calidad_aire", "ruido", "aforo"]

# Los que interesan a los vecinos de la calle.
TIPOS_VECINO = ["ruido", "aforo"]

# Nombre que se ve en pantalla para cada tipo.
NOMBRE_SENSOR = {
    "temperatura": "Temperatura",
    "humedad": "Humedad",
    "calidad_aire": "Calidad del aire",
    "ruido": "Ruido",
    "aforo": "Aforo",
}

# Unidad de medida de cada tipo.
UNIDAD_SENSOR = {
    "temperatura": "°C",
    "humedad": "%",
    "calidad_aire": "ppm",
    "ruido": "dB",
    "aforo": "personas",
}

# Color del diodo LED que enciende cada tipo cuando hay alerta (ruido y aforo no tienen LED).
LED_SENSOR = {
    "temperatura": "rojo",
    "humedad": "azul",
    "calidad_aire": "verde",
}

# ----------------------------------------------------------------------
# UMBRALES: a partir de qué valor hay PRECAUCIÓN (amarillo) o PELIGRO (rojo).
# Si hay que cambiar algún número, solo se cambia aquí.
#   "precaucion" y "peligro"                -> se supera si el valor es MAYOR.
#   "precaucion_minima" y "peligro_minimo"  -> se supera si el valor es MENOR.
# El aforo va en % del aforo máximo de cada local.
# El CO2 no tiene decimales: "más de 799" es lo mismo que "desde 800".
# ----------------------------------------------------------------------
UMBRALES = {
    "temperatura": {"precaucion": 27, "peligro": 30},
    "humedad": {"precaucion": 65, "peligro": 70, "precaucion_minima": 35, "peligro_minimo": 30},
    "calidad_aire": {"precaucion": 799, "peligro": 1199},
    "ruido": {"precaucion": 65, "peligro": 80},
    "aforo": {"precaucion": 80, "peligro": 100},
}

# Nombre de la calidad del aire según el color de su semáforo.
CALIDAD_AIRE = {"verde": "Buena", "amarillo": "Moderada", "rojo": "Mala"}


def sensores_actuales(codigo=""):
    """Los sensores de un local (o de todos) con su última medida: id, local, tipo, valor y fecha."""
    return consultar(
        """
        SELECT s.id, s.local, s.tipo, m.valor, m.fecha
        FROM sensores s
        JOIN medidas m ON m.id = (SELECT MAX(id) FROM medidas WHERE sensor = s.id)
        WHERE ? IN ('', s.local)
        ORDER BY s.id
        """,
        (codigo,),
    )


def historial_de(codigo, tipo, cantidad):
    """Las últimas medidas de un sensor, de la más nueva a la más antigua."""
    return consultar(
        """
        SELECT m.valor, m.fecha
        FROM medidas m JOIN sensores s ON s.id = m.sensor
        WHERE s.local = ? AND s.tipo = ?
        ORDER BY m.id DESC LIMIT ?
        """,
        (codigo, tipo, cantidad),
    )


def insertar_sensor(codigo, tipo):
    """Da un sensor nuevo a un local y devuelve su id."""
    return insertar("sensores", {"local": codigo, "tipo": tipo})


def insertar_medida(id_sensor, valor, fecha):
    """Guarda una medida de un sensor."""
    insertar("medidas", {"sensor": id_sensor, "valor": valor, "fecha": fecha})
