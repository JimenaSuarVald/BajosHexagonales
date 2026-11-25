# Roles de usuario — Bajos de Argüelles

La aplicación tiene **tres roles**. Cada usuario elige el suyo al registrarse y
no se puede cambiar después. El rol decide **qué datos tiene que dar al
registrarse** y **qué puede hacer** dentro de la aplicación.

---

## 1. Vecino

**Quién es:** una persona que vive en la zona de Argüelles.

**Registro:** nombre, correo, contraseña y su **calle** (por ejemplo `Calle Ferraz`). Puede cambiarla después desde su panel.

**Qué puede hacer:**
- Ver la lista de locales de la zona (nombre, tipo, dirección y aforo).
- Ver el semáforo de todos los locales.
- Consultar el **ruido y el aforo** de los locales de su calle, con su gráfico.

**Qué NO puede hacer:** crear, modificar ni eliminar locales; ver el resto de sensores ni las incidencias.

---

## 2. Propietario

**Quién es:** el dueño o responsable de un local (bar, restaurante, discoteca...).

**Registro:** además de nombre, correo y contraseña, debe introducir el
**código de negocio** de su local (por ejemplo `NEG-001`).

El registro solo se acepta si se cumplen estas condiciones:

| Comprobación | Mensaje si falla |
|---|---|
| Ha escrito un código | "Los propietarios deben introducir su código de negocio." |
| El código pertenece a un local que existe | "Ese código de negocio no corresponde a ningún local." |
| Ese local no tiene ya otro propietario | "Ese local ya tiene un propietario registrado." |

> **¿De dónde sale el código?** Lo crea la **Autoridad** al dar de alta el
> local, y se lo entrega al propietario. Así nadie puede registrarse como
> dueño de un local que no es suyo.

**Qué puede hacer:**
- Ver la lista de todos los locales.
- **Editar los datos de SU local** (nombre, dirección, tipo y aforo). El código
  de negocio no se puede cambiar.

- Ver los **5 sensores, gráficos e incidencias de SU local** y reclamar sus cierres.

**Qué NO puede hacer:** crear locales, eliminarlos, editar locales de otros ni ver sus sensores (de los demás solo ve el semáforo).

---

## 3. Autoridad

**Quién es:** un agente de policía o persona del Ayuntamiento encargada de
supervisar la zona.

**Registro:** además de nombre, correo y contraseña, debe introducir su
**ID de identificación policial** (por ejemplo `POL-0001`).

El registro solo se acepta si se cumplen estas condiciones:

| Comprobación | Mensaje si falla |
|---|---|
| Ha escrito un ID | "La autoridad debe introducir su ID de identificación policial." |
| El ID está en la lista oficial (tabla `ids_policiales`) | "Ese ID policial no es válido." |
| Ese ID no lo usa ya otra cuenta | "Ese ID policial ya está registrado." |

> **Lista oficial de IDs.** En este prototipo es el archivo
> la tabla `ids_policiales` de la base de datos (sus datos iniciales están en
> `src/models/ids_policiales.json`). Para autorizar a un agente nuevo basta con
> añadir su ID a esa tabla. En una versión real se consultaría un registro oficial.

**Qué puede hacer (gestión completa de locales, CRUD):**
- **Crear** locales nuevos (y con ello su código de negocio).
- **Ver** todos los locales.
- **Modificar** cualquier local.
- **Eliminar** cualquier local (pide confirmación antes).
- **Supervisar los sensores de toda la zona**: resumen, comparación, alertas e incidencias.
- Cerrar y reabrir locales, y resolver reclamaciones.
- Usar el simulador de pruebas.

---

## Tabla resumen de permisos

| Acción sobre locales | Vecino | Propietario | Autoridad |
|---|:---:|:---:|:---:|
| Ver la lista | ✅ | ✅ | ✅ |
| Crear | ❌ | ❌ | ✅ |
| Modificar | ❌ | Solo el suyo | ✅ Todos |
| Eliminar | ❌ | ❌ | ✅ |
| Ver el semáforo | ✅ | ✅ | ✅ |
| Ver sensores e incidencias | Solo ruido y aforo de su calle | Solo los de su local | ✅ Todos |
| Cerrar y reabrir | ❌ | ❌ | ✅ |
| Reclamar un cierre | ❌ | Solo el suyo | ❌ |
| Usar el simulador | ❌ | ❌ | ✅ |

## Dato que guarda cada rol

| Rol | Campo especial en la tabla `usuarios` | Ejemplo |
|---|---|---|
| Vecino | `calle` | `"Calle Ferraz"` |
| Propietario | `codigo_negocio` | `"NEG-001"` |
| Autoridad | `id_policial` | `"POL-0001"` |

## Dónde está en el código

| Qué | Archivo | Función |
|---|---|---|
| Lista de roles | `src/models/usuario.py` | `ROLES` |
| Comprobaciones del registro por rol | `src/controllers/login_controller.py` | `registrar()` |
| Permisos sobre locales | `src/controllers/local_controller.py` | `puede_crear()`, `puede_editar()`, `puede_eliminar()`, `puede_ver_sensores()` |
| Campo que aparece según el rol | `src/views/register_view.py` | `cambiar_rol()` |
| Botones que ve cada rol | `src/views/locales_view.py` | `tarjeta()`, `construir()` |

## Usuarios de prueba

Se crean solos la primera vez que se abre la aplicación (contraseña `1234`):

| Rol | Correo | Código |
|---|---|---|
| Vecino | `vecino@arguelles.es` | Calle `Calle Ferraz` |
| Propietario | `bar@arguelles.es` | Negocio `NEG-001` (local "Bar Demo") |
| Autoridad | `ayto@arguelles.es` | ID policial `POL-0001` |

IDs policiales libres para probar el registro de una Autoridad: `POL-0002` a `POL-0005`.
Para registrar un Propietario nuevo, primero entra como Autoridad, crea un
local (por ejemplo `NEG-002`) y usa ese código al registrarte.
