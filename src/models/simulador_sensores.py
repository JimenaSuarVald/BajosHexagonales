"""MODELO: SIMULADOR que se inventa las medidas de los sensores.

No tenemos sensores de verdad, así que este archivo genera números creíbles.
Hay dos situaciones ("escenarios"):
    "normal" -> valores tranquilos, sin alertas.
    "alerta" -> mucho calor, humedad, aire cargado, ruido y gente (para ver las alertas).
"""
# "random" viene con Python y sirve para sacar números al azar.
import random

# Entre qué valores se mueve cada sensor en cada escenario: (mínimo, máximo).
# El aforo va en % del aforo máximo del local (100 = lleno).
RANGOS = {
    "normal": {
        "temperatura": (21, 26),
        "humedad": (40, 60),
        "calidad_aire": (450, 900),
        "ruido": (45, 62),
        "aforo": (15, 70),
    },
    "alerta": {
        "temperatura": (31, 34),
        "humedad": (72, 82),
        "calidad_aire": (1300, 1700),
        "ruido": (84, 96),
        "aforo": (104, 120),
    },
}

# Sensores que se dan sin decimales; los demás llevan 1 decimal.
SIN_DECIMALES = ["calidad_aire", "aforo"]


def redondear(tipo, valor):
    """Redondea según el tipo de sensor."""
    if tipo in SIN_DECIMALES:
        return round(valor)
    return round(valor, 1)


def valor_al_azar(tipo, escenario, aforo_maximo):
    """Un valor cualquiera dentro del rango del escenario."""
    minimo, maximo = RANGOS[escenario][tipo]
    # random.uniform da un número con decimales entre minimo y maximo.
    valor = random.uniform(minimo, maximo)
    if tipo == "aforo":
        # Pasamos del % a personas.
        valor = valor * aforo_maximo / 100
    return redondear(tipo, valor)


def siguiente_valor(tipo, valor_actual, escenario, aforo_maximo):
    """La próxima medida: va a mitad de camino entre el valor actual y uno nuevo al azar.

    Así los valores cambian poco a poco, como en un sensor real, y no a saltos.
    """
    destino = valor_al_azar(tipo, escenario, aforo_maximo)
    return redondear(tipo, (valor_actual + destino) / 2)
