"""VISTA: piezas que se repiten en varias pantallas.

    cabecera(...)           -> botones de arriba, título y quién ha entrado
    seccion(...)            -> tarjeta con un título y lo que se le pase dentro
    icono_semaforo(color)   -> circulito verde, amarillo o rojo con el estado del bar
    etiqueta_cerrado()      -> cartel negro "CERRADO TEMPORALMENTE"
    led(color, encendido)   -> un diodo LED (encendido = color vivo; apagado = gris)
    grafico_lineas(...)     -> cómo ha ido cambiando un sensor
    grafico_barras(...)     -> compara el valor de varios bares
    tarjeta_sensor(...)     -> valor, gráfico y estadísticas de un sensor
    tabla_incidencias(...)  -> log de incidencias
    ventana_texto(...)      -> ventanita con una caja para escribir (motivo, reclamación...)
    pedir_cierre(...) y pedir_reapertura(...) -> ventanitas de la policía
"""
# Flet es la librería que dibuja la interfaz gráfica; "canvas" es su lienzo de dibujo.
import flet as ft
import flet.canvas as cv

# Nombres y unidades de cada tipo de sensor.
from src.models.sensor import NOMBRE_SENSOR, UNIDAD_SENSOR

# Color de Flet para cada color del semáforo.
COLOR_FLET = {"verde": ft.Colors.GREEN, "amarillo": ft.Colors.AMBER, "rojo": ft.Colors.RED}

# Qué significa cada color del semáforo.
SIGNIFICADO = {"verde": "Todo correcto", "amarillo": "Precaución", "rojo": "Nivel peligroso"}

# Color de Flet para cada LED.
COLOR_LED = {"rojo": ft.Colors.RED, "azul": ft.Colors.BLUE, "verde": ft.Colors.GREEN}

# Color de las líneas y barras de los gráficos.
COLOR_GRAFICO = ft.Colors.BLUE_700

# Icono de cada tipo de sensor.
ICONO_SENSOR = {
    "temperatura": ft.Icons.THERMOSTAT,
    "humedad": ft.Icons.WATER_DROP,
    "calidad_aire": ft.Icons.AIR,
    "ruido": ft.Icons.VOLUME_UP,
    "aforo": ft.Icons.GROUPS,
}

# Cuántas medidas salen en los gráficos y en las tablas.
MEDIDAS_EN_GRAFICO = 24
MEDIDAS_EN_TABLA = 8


# ----------------------------------------------------------------------
# PIEZAS GENERALES
# ----------------------------------------------------------------------
def cabecera(app, titulo, botones):
    """Parte de arriba de las pantallas: botones, título y quién ha entrado."""
    usuario = app.usuario
    quien = f"{usuario.nombre} · {usuario.rol}"
    # Cada rol tiene solo uno de estos tres datos; los otros están vacíos.
    for dato in (usuario.codigo_negocio, usuario.id_policial, usuario.calle):
        if dato:
            quien = f"{quien} · {dato}"
    return ft.Column(
        controls=[
            # wrap=True baja los botones a otra línea si no caben (móvil).
            ft.Row(wrap=True, controls=botones),
            ft.Text(titulo, size=24, weight=ft.FontWeight.BOLD),
            ft.Text(quien, size=13, color=ft.Colors.GREY_700),
        ]
    )


def seccion(titulo, controles, icono):
    """Tarjeta con un título y lo que se le pase dentro."""
    titulo_con_icono = ft.Row(
        controls=[ft.Icon(icono), ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, expand=True)]
    )
    return ft.Card(
        content=ft.Container(padding=20, content=ft.Column(controls=[titulo_con_icono] + controles))
    )


def icono_semaforo(color, tamano=28):
    """Circulito del color del estado del bar. Al pasar el ratón explica qué significa."""
    return ft.Icon(ft.Icons.CIRCLE, color=COLOR_FLET[color], size=tamano, tooltip=SIGNIFICADO[color])


def etiqueta_cerrado():
    """Cartel que se pone en los bares cerrados por la policía."""
    return ft.Container(
        bgcolor=ft.Colors.BLACK,
        padding=6,
        border_radius=6,
        content=ft.Row(
            tight=True,
            controls=[
                ft.Icon(ft.Icons.LOCK, color=ft.Colors.WHITE, size=16),
                ft.Text("CERRADO TEMPORALMENTE", color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.BOLD),
            ],
        ),
    )


def estado_bar(app, codigo):
    """Semáforo del bar, qué significa y, si está cerrado, el cartel."""
    color = app.sensor_controller.color_bar(codigo)
    controles = [icono_semaforo(color), ft.Text(SIGNIFICADO[color])]
    if app.vigilancia_controller.cierre_activo(codigo):
        controles.append(etiqueta_cerrado())
    return ft.Row(wrap=True, controls=controles)


def led(color, encendido, tamano=30):
    """Un diodo LED redondo."""
    if encendido:
        relleno = COLOR_LED[color]
        # La sombra del mismo color hace que parezca que brilla.
        brillo = ft.BoxShadow(blur_radius=14, spread_radius=1, color=COLOR_LED[color])
    else:
        relleno = ft.Colors.GREY_300
        brillo = None
    return ft.Container(
        width=tamano,
        height=tamano,
        border_radius=tamano / 2,
        bgcolor=relleno,
        shadow=brillo,
        border=ft.Border.all(2, COLOR_LED[color]),
    )


def fila_leds(app, codigo, tamano):
    """Los 3 LEDs y el ventilador de un bar."""
    leds = app.sensor_controller.leds(codigo)
    if app.sensor_controller.ventilador(codigo):
        ventilador = ft.Text("Ventilador ENCENDIDO", color=ft.Colors.CYAN_700, weight=ft.FontWeight.BOLD)
    else:
        ventilador = ft.Text("Ventilador apagado", color=ft.Colors.GREY_700)
    controles = []
    for color, nombre in (("rojo", "Temperatura"), ("azul", "Humedad"), ("verde", "Aire")):
        controles.append(ft.Row(tight=True, controls=[led(color, leds[color], tamano), ft.Text(nombre, size=12)]))
    return ft.Row(wrap=True, controls=controles + [ventilador])


# ----------------------------------------------------------------------
# GRÁFICOS
# ----------------------------------------------------------------------
def grafico_lineas(medidas, limites):
    """Línea con las medidas de un sensor (nos las dan de la más nueva a la más antigua)."""
    if len(medidas) < 2:
        return ft.Text("Todavía no hay medidas suficientes para el gráfico.")
    medidas = list(reversed(medidas))
    valores = []
    for medida in medidas:
        valores.append(medida["valor"])
    # La altura del gráfico va del menor al mayor, contando también los límites.
    menor = min(valores + list(limites.values()))
    mayor = max(valores + list(limites.values()))

    def dibujar(ancho, alto):
        """Devuelve las líneas del gráfico para ese tamaño."""

        # Pasa un valor a su altura en el dibujo (en pantalla, y=0 está arriba).
        def altura(valor):
            return 6 + (alto - 12) * (mayor - valor) / (mayor - menor)

        # Separación horizontal entre una medida y la siguiente.
        paso = (ancho - 12) / (len(valores) - 1)
        formas = []
        # 1. Los límites: líneas discontinuas.
        for nombre in limites:
            color = COLOR_FLET["rojo"] if nombre.startswith("peligro") else COLOR_FLET["amarillo"]
            lapiz = ft.Paint(color=color, stroke_width=1.5, stroke_dash_pattern=[6, 4])
            formas.append(cv.Line(0, altura(limites[nombre]), ancho, altura(limites[nombre]), paint=lapiz))
        # 2. Las medidas: un trocito de línea entre cada una y la siguiente.
        lapiz = ft.Paint(color=COLOR_GRAFICO, stroke_width=2, stroke_cap=ft.StrokeCap.ROUND)
        for i in range(len(valores) - 1):
            formas.append(
                cv.Line(6 + i * paso, altura(valores[i]), 6 + (i + 1) * paso, altura(valores[i + 1]), paint=lapiz)
            )
        # 3. Un punto en la última medida.
        formas.append(cv.Circle(ancho - 6, altura(valores[-1]), 4, paint=ft.Paint(color=COLOR_GRAFICO)))
        return formas

    def cambiar_tamano(evento):
        # Flet avisa del tamaño real del lienzo: lo volvemos a dibujar a esa medida.
        lienzo.shapes = dibujar(evento.width, evento.height)
        lienzo.update()

    lienzo = cv.Canvas(shapes=dibujar(260, 130), on_resize=cambiar_tamano, expand=True)
    return ft.Column(
        spacing=2,
        controls=[
            ft.Row(
                height=130,
                controls=[
                    # Números de la izquierda: el mayor arriba y el menor abajo.
                    ft.Column(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Text(f"{mayor:g}", size=11), ft.Text(f"{menor:g}", size=11)],
                    ),
                    lienzo,
                ],
            ),
            # Fechas de la primera y la última medida (sin el año).
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[ft.Text(medidas[0]["fecha"][5:], size=11), ft.Text(medidas[-1]["fecha"][5:], size=11)],
            ),
        ],
    )


def grafico_barras(filas):
    """Una barra por bar. Cada fila es (nombre, valor, color del semáforo)."""
    mayor = 0
    for nombre, valor, color in filas:
        mayor = max(mayor, valor)
    barras = []
    for nombre, valor, color in filas:
        barras.append(
            ft.Row(
                controls=[
                    icono_semaforo(color, 14),
                    ft.Text(nombre, width=110, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    # value va de 0 (vacía) a 1 (llena). Si todos valen 0, queda vacía.
                    ft.ProgressBar(value=valor / mayor if mayor else 0, color=COLOR_GRAFICO, bar_height=12, expand=True),
                    ft.Text(f"{valor:g}", width=50, size=13),
                ]
            )
        )
    return ft.Column(controls=barras)


# ----------------------------------------------------------------------
# PIEZAS CON DATOS
# ----------------------------------------------------------------------
def tarjeta_sensor(app, codigo, tipo, con_tabla=False):
    """Un sensor: valor actual, gráfico, estadísticas y, si se pide, tabla de medidas."""
    sensores = app.sensor_controller
    unidad = UNIDAD_SENSOR[tipo]
    valor = sensores.valor(codigo, tipo)
    color = sensores.color_sensor(codigo, tipo, valor)
    limites = sensores.limites(codigo, tipo)
    medidas = sensores.historial_de(codigo, tipo, MEDIDAS_EN_GRAFICO)

    estado = SIGNIFICADO[color]
    if tipo == "calidad_aire":
        estado = f"{estado} (calidad {sensores.calidad_aire(valor)})"
    controles = [
        ft.Row(controls=[ft.Icon(ICONO_SENSOR[tipo]), ft.Text(NOMBRE_SENSOR[tipo], weight=ft.FontWeight.BOLD)]),
        ft.Row(
            wrap=True,
            controls=[
                icono_semaforo(color),
                ft.Text(f"{valor} {unidad}", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(estado),
            ],
        ),
        grafico_lineas(medidas, limites),
    ]
    resumen = sensores.estadisticas(medidas)
    if resumen:
        minimo, media, maximo = resumen
        controles.append(ft.Text(f"Mínimo {minimo} · Media {media} · Máximo {maximo}", size=12))
    # Explicación de las líneas discontinuas.
    precaucion = f"más de {limites['precaucion']:g}"
    peligro = f"más de {limites['peligro']:g}"
    if "peligro_minimo" in limites:
        precaucion = f"{precaucion} o menos de {limites['precaucion_minima']:g}"
        peligro = f"{peligro} o menos de {limites['peligro_minimo']:g}"
    controles.append(
        ft.Text(
            f"Últimas {len(medidas)} medidas. Amarillo, precaución: {precaucion}. Rojo, peligro: {peligro}.",
            size=11,
            color=ft.Colors.GREY_700,
        )
    )
    if con_tabla:
        filas = []
        for medida in medidas[:MEDIDAS_EN_TABLA]:
            color_medida = sensores.color_sensor(codigo, tipo, medida["valor"])
            filas.append([medida["fecha"], f"{medida['valor']} {unidad}", SIGNIFICADO[color_medida]])
        controles.append(tabla(["Fecha", "Valor", "Estado"], filas))
    return ft.Card(
        # 1 tarjeta por fila en móvil, 2 en tablet, 3 en pantalla grande.
        col={"xs": 12, "md": 6, "lg": 4},
        content=ft.Container(padding=16, content=ft.Column(controls=controles)),
    )


def tabla(titulos, filas):
    """Tabla de textos, con scroll horizontal por si no cabe a lo ancho (móvil)."""
    columnas = []
    for titulo in titulos:
        columnas.append(ft.DataColumn(titulo))
    filas_flet = []
    alto = 32
    for fila in filas:
        celdas = []
        for texto in fila:
            ancho = None
            # Los textos largos (descripciones) se limitan a 380 para que bajen de línea.
            if len(texto) > 60:
                ancho = 380
                alto = 70
            celdas.append(ft.DataCell(ft.Text(texto, size=13, width=ancho)))
        filas_flet.append(ft.DataRow(cells=celdas))
    return ft.Row(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.DataTable(
                column_spacing=16,
                data_row_min_height=32,
                data_row_max_height=alto,
                columns=columnas,
                rows=filas_flet,
            )
        ],
    )


def tabla_incidencias(app, incidencias):
    """Log de incidencias (de un bar o de toda la zona)."""
    if not incidencias:
        return ft.Text("No hay incidencias.")
    filas = []
    for incidencia in incidencias:
        filas.append(
            [
                incidencia["fecha"],
                app.local_controller.nombre_de(incidencia["local"]),
                incidencia["tipo"],
                incidencia["autor"],
                incidencia["descripcion"],
            ]
        )
    return tabla(["Fecha", "Local", "Tipo", "Autor", "Descripción"], filas)


# ----------------------------------------------------------------------
# VENTANITAS
# ----------------------------------------------------------------------
def ventana_texto(app, titulo, explicacion, texto_boton, al_aceptar):
    """Abre una ventanita para escribir un texto (motivo de cierre, reclamación...).

    "al_aceptar" es una función que recibe lo escrito y devuelve "" si todo ha
    ido bien, o un mensaje de error. Si hay error, se muestra y la ventana sigue abierta.
    Si va bien, la ventana se cierra y la pantalla se vuelve a dibujar.
    """
    caja = ft.TextField(label="Escribe aquí", multiline=True, min_lines=2, max_lines=6)
    texto_error = ft.Text(color=ft.Colors.RED)

    # Esta función se ejecuta al pulsar el botón principal de la ventana.
    def aceptar(evento):
        error = al_aceptar(caja.value or "")
        if error:
            texto_error.value = error
            app.page.update()
        else:
            app.page.pop_dialog()
            app.recargar()

    dialogo = ft.AlertDialog(
        title=ft.Text(titulo),
        # 420 de ancho, o menos si la ventana es más estrecha (móvil).
        content=ft.Column(
            tight=True,
            width=min(420, (app.page.width or 420) - 80),
            controls=[ft.Text(explicacion), caja, texto_error],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda evento: app.page.pop_dialog()),
            ft.FilledButton(texto_boton, on_click=aceptar),
        ],
    )
    app.page.show_dialog(dialogo)


def pedir_cierre(app, local):
    """(Autoridad) Pide el motivo y cierra el bar."""

    # Esta función recibe el texto escrito en la ventanita.
    def al_aceptar(motivo):
        error = app.vigilancia_controller.cerrar_local(app.usuario, local.codigo, motivo)
        if not error:
            # Al cerrar, el bar se vacía: sus sensores vuelven a valores normales.
            app.sensor_controller.simular(app.usuario, local.codigo, "normal")
        return error

    ventana_texto(
        app,
        f"Cerrar temporalmente {local.nombre}",
        "Escribe la incidencia que justifica el cierre. El propietario la recibirá.",
        "Cerrar local",
        al_aceptar,
    )


def pedir_reapertura(app, codigo):
    """(Autoridad) Reabre un bar, con una nota opcional."""
    ventana_texto(
        app,
        f"Reabrir {app.local_controller.nombre_de(codigo)}",
        "Puedes escribir una nota para el propietario (opcional).",
        "Reabrir",
        lambda nota: app.vigilancia_controller.reabrir_local(app.usuario, codigo, nota),
    )
