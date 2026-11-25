# Guía del código — Sensores, alertas policiales y cierres

Esta parte de la aplicación añade:

1. **Sensores simulados en todos los bares** (temperatura, humedad, calidad del aire, ruido y aforo), guardados en la base de datos con su **historial** y sus **gráficos**.
2. **Semáforo** en cada local: 🟢 verde, 🟡 amarillo o 🔴 rojo.
3. **LEDs de alerta**: 🔴 rojo por temperatura, 🔵 azul por humedad y 🟢 verde por calidad del aire.
4. **Ventilador**, que se enciende con más de 30 °C **y** el aire «Malo» a la vez.
5. **Alertas a la policía** cuando un bar llega a niveles peligrosos.
6. **Cierre temporal** de un bar por la policía, que antes tiene que escribir el motivo.
7. **Log de incidencias** de cada bar.
8. **Notificaciones** al propietario cuando cierran su bar, con el motivo.
9. **Reclamaciones**: el propietario reclama y la policía decide si el cierre fue justificado o no.

El código sigue el mismo estilo que el resto del proyecto: **MVC**, comentarios en cada bloque y lo más sencillo posible. Si no sabes nada de Python, lee primero los apartados 1 y 2 de `docs/GUIA_DEL_CODIGO.md`.

---

## 1. Cómo probarlo

Desde la carpeta `Proyecto-Informatica-Grupo5`:

```bash
python main.py
```

Se abre la aplicación de siempre (con el mismo login y los mismos usuarios), con el panel de sensores como pantalla principal. Usuarios de prueba (contraseña `1234`):

| Rol | Correo | Qué ver |
|---|---|---|
| Autoridad | `ayto@arguelles.es` | Resumen y comparación de la zona, alertas, cerrar bares, reclamaciones, incidencias |
| Propietario | `bar@arguelles.es` (local `NEG-001`) | «Mi local», sus 5 sensores con gráficos, incidencias y botón de reclamación |
| Vecino | `vecino@arguelles.es` | Ruido y aforo de los bares de su calle; semáforo de toda la zona |

**Prueba completa paso a paso:**

1. Entra como **Autoridad** → *Ver sensores e incidencias* en «Bar Demo» → **Forzar alerta** → pulsa **Actualizar medidas** 3 o 4 veces. Los valores suben, los LEDs se encienden, el semáforo se pone rojo y el ventilador se enciende.
2. **Volver** al panel: aparece una notificación y el bar sale en «Alertas de niveles peligrosos».
3. Pulsa **Cerrar temporalmente**, escribe el motivo (mínimo 20 letras) y confirma.
4. **Cerrar sesión** y entra como **Propietario**: verás el aviso del cierre con el motivo y el botón **Presentar reclamación**.
5. Escribe la reclamación, cierra sesión y entra otra vez como **Autoridad**: aparece en «Reclamaciones pendientes». Elige **Justificado** (el bar sigue cerrado) o **No justificado** (el bar se reabre). El propietario recibe la respuesta.
6. En el detalle del bar, el **Log de incidencias** muestra todo lo ocurrido.

---

## 2. Archivos

Todos están en `src`, junto al resto del código:

```
main.py                               Arranca App
src/
├── app.py                            Cambia de pantalla, toma medidas y recarga
├── models/                           MODELO (datos y base de datos)
│   ├── base_datos.py                 Base de datos: tablas y consultas
│   ├── sensor.py                     Sensores, medidas y UMBRALES
│   ├── simulador_sensores.py         Se inventa las medidas
│   ├── vigilancia.py                 Incidencias, cierres y notificaciones
│   └── sensores.json, historial_sensores.json, incidencias.json, notificaciones.json
│                                     Datos iniciales (historial previo) que se copian a la base de datos
├── controllers/                      CONTROLADOR (reglas)
│   ├── sensor_controller.py          Semáforo, LEDs, ventilador, medidas
│   └── vigilancia_controller.py      Alertas, cierres, reclamaciones, notificaciones
└── views/                            VISTA (pantallas)
    ├── piezas_sensores.py            Piezas repetidas: cabecera, semáforo, LED, gráficos, tablas, ventanitas
    ├── panel_sensores_view.py        Panel principal según el rol
    ├── bar_sensores_view.py          Detalle de un bar
    └── locales_view.py               Lista de locales (CRUD) con su semáforo
```

**Orden recomendado de lectura:** `models/base_datos.py` → `models/sensor.py` → `models/simulador_sensores.py` → `models/vigilancia.py` → `controllers/sensor_controller.py` → `controllers/vigilancia_controller.py` → `app.py` → las vistas.

Al crear un local con el CRUD se le dan sus 5 sensores en ese momento. Al eliminarlo se borran también sus sensores, historial, incidencias, cierres y avisos.

---

## 3. Los datos (base de datos)

Todo está en la base de datos (ver el apartado 5 de `GUIA_DEL_CODIGO.md`).

| Tabla | Qué guarda |
|---|---|
| `sensores` | Los 5 sensores de cada local |
| `medidas` | **Todas** las medidas de cada sensor. La última es su valor actual |
| `incidencias` | El **log** de cada bar: fecha, tipo, autor y descripción |
| `cierres` | Los cierres de la policía: motivo, si sigue activo, la reclamación, su estado y la respuesta |
| `notificaciones` | Avisos para un propietario (`local` = su código) o para la policía (`local` vacío) |

- **Historial previo:** al crear la base de datos se copian los JSON iniciales. Incluyen 25 medidas, una por hora, de cada uno de los 5 sensores del Bar Demo (del 12 al 13 de noviembre). También incluyen una alerta a medianoche con su normalización y el aviso a la policía.
- Un bar sin sensores (por ejemplo, uno creado con el CRUD) recibe al momento sus 5 sensores con un **historial de 24 horas** (una medida por hora). Entre las 23:00 y la 01:59 el bar está lleno, así que en esas horas salen valores peligrosos.

---

## 4. Reglas: semáforo, LEDs y ventilador (`sensor_controller.py`)

Todos los números están en `UMBRALES`, al principio de `models/sensor.py`. Si hay que cambiarlos, solo se cambian ahí.

| Sensor | 🟢 Verde | 🟡 Amarillo (precaución) | 🔴 Rojo (peligro) | LED |
|---|---|---|---|---|
| Temperatura | hasta 27 °C | de 27 a 30 °C | **más de 30 °C** | 🔴 rojo |
| Humedad | 35 % a 65 % | 30–35 % o 65–70 % | **menos de 30 % o más de 70 %** | 🔵 azul |
| Calidad del aire (CO2) | «Buena»: menos de 800 ppm | «Moderada»: 800–1199 ppm | **«Mala»: 1200 ppm o más** | 🟢 verde |
| Ruido | hasta 65 dB | de 65 a 80 dB | **más de 80 dB** | — |
| Aforo | hasta el 80 % del máximo del local | del 80 al 100 % | **más del 100 %** | — |

- **Semáforo del bar** = el peor color de sus 5 sensores.
- **LED**: se enciende cuando su sensor está en rojo.
- **Ventilador**: se enciende con temperatura > 30 °C **y** aire «Mala» (las dos cosas a la vez).

| Función | Qué devuelve |
|---|---|
| `color_sensor(codigo, tipo, valor)` | `"verde"`, `"amarillo"` o `"rojo"` |
| `color_bar(codigo)` | El color del bar |
| `leds(codigo)` | `{"rojo": True, "azul": False, "verde": True}` |
| `ventilador(codigo)` | `True` o `False` |
| `medir_todos()` | Toma una medida nueva en todos los bares |
| `limites(codigo, tipo)` | Los umbrales del sensor (los del aforo, en personas de ese local) |
| `historial_de(codigo, tipo, cantidad)` / `estadisticas(medidas)` | Datos de los gráficos y su mínimo, media y máximo |
| `simular(usuario, codigo, escenario)` | Solo Autoridad. `"alerta"` o `"normal"`: hacia dónde van las próximas medidas |
| `preparar_sensores()` (función suelta) | Da a cada bar los sensores que le falten |

Las medidas **no cambian solas**: cambian al iniciar sesión y cada vez que se pulsa **Actualizar medidas**. Los valores van cambiando poco a poco, como en un sensor real.

---

## 5. Policía, cierres y reclamaciones (`vigilancia_controller.py`)

Igual que `LocalController`, las funciones que cambian algo devuelven `""` si ha ido bien, o el texto del error. **Los permisos se comprueban aquí**, no solo escondiendo botones.

| Función | Quién | Qué hace |
|---|---|---|
| `revisar_alertas()` | Automático, tras cada medida | Si un bar pasa a **rojo**: lo apunta en su log y **avisa a la policía**. Si vuelve a la normalidad, lo apunta también. Solo avisa una vez por alerta. |
| `cerrar_local(usuario, codigo, motivo)` | Autoridad | Exige un **motivo de 20 letras como mínimo**. Guarda el cierre, lo apunta en el log y **avisa al propietario con el motivo**. |
| `reabrir_local(usuario, codigo, nota)` | Autoridad | Reabre el bar y avisa al propietario. |
| `reclamar(usuario, codigo, texto)` | Propietario de ese bar | Una reclamación por cierre. Queda «Pendiente» y **avisa a la policía**. |
| `resolver_reclamacion(usuario, codigo, justificado, respuesta)` | Autoridad | **Justificado**: el bar sigue cerrado. **No justificado**: el bar se reabre. El propietario recibe la respuesta. |
| `incidencias_de(codigo)` | Autoridad y Propietario de ese bar | El log del bar, lo más nuevo primero. |
| `todas_las_incidencias(tipo, cantidad)` | Autoridad | El log de toda la zona. |
| `notificaciones_de(usuario)` / `marcar_leidas(usuario)` | Autoridad y Propietario | Sus avisos. |

Recorrido de un cierre con reclamación:

```
Sensores en ROJO ─► revisar_alertas() ─► log "Nivel peligroso" + aviso a la POLICÍA
                                                     │
Policía: "Cerrar temporalmente" + motivo ─► cerrar_local() ─► log "Cierre temporal"
                                                     └──────► aviso al PROPIETARIO (con el motivo)
                                                                     │
Propietario: "Presentar reclamación" ─► reclamar() ─► log "Reclamación" + aviso a la POLICÍA
                                                                     │
Policía: "Justificado" ──────► sigue cerrado ─┐
Policía: "No justificado" ───► se reabre ─────┴► log "Resolución" + aviso al PROPIETARIO
```

---

## 6. Las pantallas

| Pantalla | Archivo | Quién | Qué tiene |
|---|---|---|---|
| Panel principal | `panel_sensores_view.py` | Todos | *Actualizar medidas* y lista de bares con semáforo, buscador y filtro |
| | | Vecino | + **Mi calle**: ruido y aforo (con gráfico) de los bares de su calle |
| | | Propietario | + Notificaciones, **Mi local** (aforo, cierre y reclamación), sus 5 sensores con gráfico e incidencias |
| | | Autoridad | + **Resumen de la zona**, alertas, reclamaciones, bares cerrados, notificaciones, **comparación de bares** e incidencias de la zona |
| Detalle de un bar | `bar_sensores_view.py` | Autoridad y Propietario de ese bar | LEDs, ventilador, los 5 sensores con gráfico y tabla, y log. Solo la Autoridad: *Cerrar*, *Reabrir* y simulador |
| Lista de locales | `locales_view.py` | Todos | CRUD + semáforo y cartel de cerrado. *Ver sensores*, solo si tiene permiso |

Los gráficos (`grafico_lineas` y `grafico_barras`, en `piezas_sensores.py`) se dibujan con Flet, sin instalar nada más.

`piezas_sensores.py` tiene `ventana_texto(...)`: la ventanita donde se escribe el motivo, la reclamación o la respuesta. Si el controlador devuelve un error (por ejemplo, un motivo demasiado corto), lo muestra en rojo y la ventana no se cierra.

`App.recargar()` vuelve a dibujar la pantalla que se está viendo después de cada acción.
