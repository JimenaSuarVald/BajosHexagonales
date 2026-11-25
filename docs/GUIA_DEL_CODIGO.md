# Guía del código — Sprint 3

Esta guía explica cómo está organizado el código y cómo viajan los datos de
un archivo a otro. **Cada línea de código lleva además un comentario** (las
líneas que empiezan por `#`) que explica qué hace. Lee primero esta guía y
después abre los archivos en el orden del apartado 4.

---

## 1. Lo mínimo de Python para entender el código

| Lo que ves | Qué significa |
|---|---|
| `# texto` | Comentario. Python lo ignora; es solo para personas. |
| `"""texto"""` | Comentario largo al principio de un archivo o función. |
| `x = 5` | Guarda el valor 5 con el nombre `x` (una *variable*). |
| `import json` / `from a import b` | Trae herramientas de otro archivo o de Python. |
| `def nombre(datos):` | Define una *función*: un bloque de pasos con nombre que se puede usar muchas veces. |
| `return x` | La función termina y entrega `x` a quien la llamó. |
| `class Local:` | Un *molde* que describe qué datos tiene una cosa (un local, un usuario...). |
| `self.nombre` | Un dato que pertenece a ese objeto concreto ("el nombre de *este* local"). |
| `if ...:` / `elif ...:` / `else:` | "Si pasa esto... / si no, si pasa esto otro... / si no...". |
| `for x in lista:` | Repite los pasos de dentro una vez por cada elemento de la lista. |
| `[]` | Lista vacía. `lista.append(x)` añade `x` al final. |
| `{"clave": valor}` | Diccionario: parejas nombre → valor. Cada fila de la base de datos llega así. |
| `None` | "Nada". Se usa cuando algo no existe o ha fallado. |
| `not x` | Verdadero si `x` está vacío, es `None` o es `False`. |
| `f"Hola {nombre}"` | Texto que mete dentro el valor de `nombre`. |
| `try:` / `except:` | "Intenta esto; si da este error, haz esto otro". |
| La sangría (espacios a la izquierda) | Indica qué líneas están *dentro* de un `if`, `for`, `def` o `class`. |

---

## 2. Arquitectura MVC

El proyecto separa el código en tres capas para que cada archivo haga una sola cosa:

```
 VISTA (views/)          CONTROLADOR (controllers/)        MODELO (models/)
 Lo que se ve      ───►  Comprueba datos y permisos  ───►  Guarda y lee
 (botones, cajas)  ◄───  y decide qué hacer          ◄───  la base de datos
```

- **Modelo**: describe los datos (`Usuario`, `Local`) y los lee/escribe en la base de datos.
- **Controlador**: las reglas. Por ejemplo, "solo la Autoridad puede borrar" o "el aforo debe ser un número".
- **Vista**: dibuja la pantalla con Flet y, cuando se pulsa un botón, llama al controlador.

Una vista **nunca** usa la base de datos y un modelo **nunca** dibuja nada.

---

## 3. Estructura de carpetas

```
main.py                         Arranca la aplicación
src/
├── app.py                      Cambia de pantalla y recuerda quién ha entrado
├── models/
│   ├── lista_enlazada.py       ★ SPRINT 3 · Lista de nodos enlazados (maneja todos los datos)
│   ├── base_datos.py           ★ SPRINT 3 · Base de datos SQLite: tablas, consultas y transacciones
│   ├── bajos_arguelles.db      ★ SPRINT 3 · La base de datos (se crea sola; no se sube a GitHub)
│   ├── usuario.py              Usuario + roles (ahora con código de negocio / ID policial)
│   ├── local.py                ★ NUEVO · Local (bar, restaurante...)
│   ├── ids_policiales.json     Datos iniciales: lista oficial de IDs policiales válidos
│   ├── usuarios.json           Datos iniciales de versiones anteriores (no se sube a GitHub)
│   ├── locales.json            Datos iniciales de versiones anteriores (no se sube a GitHub)
│   ├── sensor.py               ★ SENSORES · Sensores, historial y umbrales
│   ├── simulador_sensores.py   ★ SENSORES · Se inventa las medidas
│   ├── vigilancia.py           ★ SENSORES · Incidencias, cierres y notificaciones
│   └── sensores.json, historial_sensores.json, incidencias.json, notificaciones.json
│                               Datos iniciales: historial previo de los sensores
├── controllers/
│   ├── user_controller.py      Crea y busca usuarios, protege contraseñas
│   ├── login_controller.py     Registro (con reglas por rol) e inicio de sesión
│   ├── local_controller.py     ★ NUEVO · CRUD de locales + permisos por rol
│   ├── sensor_controller.py    ★ SENSORES · Semáforo, LEDs, ventilador y medidas
│   └── vigilancia_controller.py ★ SENSORES · Alertas, cierres y reclamaciones
└── views/
    ├── login_view.py           Pantalla de inicio de sesión
    ├── register_view.py        Registro (el campo extra cambia según el rol)
    ├── locales_view.py         ★ NUEVO · Lista de locales con botones según el rol
    ├── local_form_view.py      ★ NUEVO · Formulario para crear / editar un local
    ├── piezas_sensores.py      ★ SENSORES · Cabecera, semáforo, LED, gráficos, tablas y ventanitas
    ├── panel_sensores_view.py  ★ SENSORES · Panel principal según el rol
    └── bar_sensores_view.py    ★ SENSORES · Detalle de un bar
tests/
└── pruebas.py                  ★ SPRINT 3 · Pruebas automáticas
docs/
├── ROLES.md                    Documentación de los roles
├── GUIA_DEL_CODIGO.md          Este documento
└── GUIA_SENSORES.md            ★ SENSORES · Explicación de sensores, alertas y cierres
```

Los archivos marcados con «SENSORES» se explican en [`GUIA_SENSORES.md`](GUIA_SENSORES.md).

---

## 4. Orden recomendado de lectura

1. `src/models/lista_enlazada.py` y `src/models/base_datos.py`: cómo se manejan los datos y cómo se guardan.
2. `src/models/local.py` y `src/models/usuario.py`: qué datos tiene cada cosa.
3. `src/controllers/user_controller.py`: crear y buscar usuarios.
4. `src/controllers/local_controller.py`: el CRUD y los permisos.
5. `src/controllers/login_controller.py`: las reglas del registro por rol.
6. `src/app.py`: cómo se pasa de una pantalla a otra.
7. Las vistas, empezando por `register_view.py` y `locales_view.py`.

---

## 5. La base de datos

Los datos se guardan en una base de datos **SQLite** (`src/models/bajos_arguelles.db`).
SQLite viene con Python: no hay que instalar nada. Las tablas están en `ESQUEMA`, al
principio de `base_datos.py`:

```
locales ─┬─< sensores ─< medidas          ─< = "uno a muchos"
         ├─< incidencias                   (un local tiene muchos sensores,
         ├─< cierres                        un sensor tiene muchas medidas...)
         ├─< notificaciones
         └─< usuarios (propietario)    ids_policiales ─< usuarios (autoridad)
```

| Tabla | Qué guarda | Clave |
|---|---|---|
| `locales` | Código, nombre, dirección, tipo y aforo | `codigo` |
| `usuarios` | Datos de cada cuenta | `email` |
| `ids_policiales` | Lista oficial de IDs | `id` |
| `sensores` | Qué sensores tiene cada local | `id` (y `local` + `tipo` no se repiten) |
| `medidas` | **Todas** las medidas: es el historial. La última es el valor actual | `id` |
| `incidencias`, `cierres`, `notificaciones` | Vigilancia (ver `GUIA_SENSORES.md`) | `id` |

- **Claves ajenas** (`REFERENCES`): no se puede guardar, por ejemplo, un sensor de un local que no existe.
- **`ON DELETE CASCADE`**: al borrar un local se borran solos sus sensores, medidas, incidencias, cierres y avisos.
- **Índices**: hacen rápidas las búsquedas más usadas (medidas de un sensor, incidencias de un local...). Uno de ellos impide que un local tenga dos cierres activos.

Todo pasa por las funciones de `base_datos.py`:

| Función | Qué hace |
|---|---|
| `consultar(sql, datos)` | Lee y devuelve una **lista enlazada** de diccionarios |
| `consultar_uno(sql, datos)` | Igual, pero solo la primera fila |
| `ejecutar(sql, datos)` / `insertar(tabla, fila)` | Cambia o añade datos |
| `transaccion()` | Junta varios cambios: o se guardan todos o ninguno |

Los datos van siempre aparte, con `?`: `consultar("SELECT * FROM locales WHERE codigo = ?", (codigo,))`.
Así un texto escrito por el usuario nunca se ejecuta como SQL.

**Transacciones.** Cerrar un local guarda tres cosas: el cierre, la línea del log y el aviso al
propietario. Van dentro de `with transaccion():`. Si una falla, se deshacen las tres.

**Datos iniciales.** La primera vez que se abre la aplicación, `preparar()` crea las tablas y
copia los datos de los JSON de `src/models`, entre ellos el **historial previo** de los sensores.
Después, los JSON ya no se usan ni se modifican. Para empezar de cero, se borra
`bajos_arguelles.db` y se vuelve a abrir la aplicación.

---

## 6. CRUD de locales

| Letra | Operación | Función en `local_controller.py` | Quién puede |
|---|---|---|---|
| C | Crear | `crear()` | Autoridad |
| R | Leer | `listar()`, `buscar()`, `de_calle()` | Todos |
| U | Actualizar | `modificar()` | Autoridad (todos) / Propietario (el suyo) |
| D | Borrar | `eliminar()` | Autoridad |

Cada operación sigue los mismos pasos:
1. **Permiso**: llama a `puede_crear` / `puede_editar` / `puede_eliminar`.
2. **Limpieza**: quita espacios y pone el código en mayúsculas.
3. **Validación**: `validar()` comprueba que no falten datos y que el aforo sea un número mayor que 0.
4. **Guardar**: lee la lista, la cambia y la vuelve a escribir.
5. **Respuesta**: devuelve `(local, "")` si ha ido bien o `(None, "mensaje de error")` si no.

Los permisos se comprueban **en el controlador**, no solo escondiendo botones
en la vista. Así, aunque alguien llamase a la función directamente, la regla se cumple.

---

## 7. Recorridos completos

### Registrar a un propietario

```
RegisterView                          LoginController.registrar()             Modelo
───────────                           ───────────────────────────             ──────
Elige rol "Propietario"
 └─ cambiar_rol() muestra la caja
    "Código de negocio"
Pulsa "Registrarme" ───────────────►  comprobaciones comunes
                                      ¿código vacío?           → error
                                      LocalController.buscar() ──────────────► tabla locales
                                      ¿no existe?              → error
                                      buscar_por_codigo_negocio() ───────────► tabla usuarios
                                      ¿ya tiene dueño?         → error
                                      crear_usuario(..., codigo_negocio) ───► tabla usuarios
app.entrar(usuario)  ◄──────────────  (usuario, "")
```

El registro de la **Autoridad** es igual, pero comprueba el ID contra
la tabla `ids_policiales` y lo guarda en `id_policial`.

### Editar un local

```
LocalesView: botón "Editar" (solo si puede_editar)
  └─ app.ir_a_editar_local(local)
       └─ LocalFormView con las cajas rellenas (código bloqueado)
            └─ "Guardar" → LocalController.modificar()
                              ├─ puede_editar()   (vuelve a comprobar el permiso)
                              ├─ validar()
                              └─ actualizar_local() ──► tabla locales
            └─ si va bien → app.ir_a_locales() (lista actualizada)
```

---

## 8. Lista de nodos enlazados

Cada dato va en un `Nodo` que sabe cuál es el anterior y cuál el siguiente:

```
primero -> [dato] <-> [dato] <-> [dato] <- ultimo
```

`consultar()` (en `base_datos.py`) devuelve siempre una `ListaEnlazada`, así que
**todos** los datos que se leen de la base de datos pasan por ella.

| Método | Qué hace |
|---|---|
| `append(dato)` / `insertar_inicio(dato)` | Añade al final / al principio |
| `buscar(condicion)` | El primer dato que cumple la condición, o `None` |
| `filtrar(condicion)` | Otra lista solo con los que la cumplen |
| `eliminar(condicion)` | Quita los que la cumplen |
| `ultimos(maximo)` | Los últimos, del más nuevo al más antiguo |

La condición es una función corta: `lambda local: local.codigo == "NEG-001"`.

---

## 9. Cómo probarlo

```bash
python -m pip install -r requirements.txt
python main.py

# Pruebas automáticas (no tocan los datos reales)
python -m unittest tests.pruebas
```

Usuarios de prueba y códigos: ver [`ROLES.md`](ROLES.md#usuarios-de-prueba).

> La base de datos no se sube a GitHub porque contiene las cuentas de los usuarios:
> cada persona la tiene en su ordenador y se crea sola al abrir la aplicación.
>
> Si vienes del Sprint 1 y ya tenías `src/models/usuarios.json`, bórralo para
> que se vuelva a crear con los usuarios de prueba nuevos (el propietario de
> prueba necesita estar unido al local `NEG-001`).
