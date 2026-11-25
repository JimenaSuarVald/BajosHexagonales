# Proyecto Informática - Grupo 5

## Descripción

Repositorio oficial del proyecto deinformatica del Grupo 5.

La gestión del proyecto se realiza siguiendo la metodología ágil Scrum y utilizando Git y GitHub como sistema de control de versiones.

---

## Estructura de ramas

El proyecto se organiza mediante las siguientes ramas:

### MAIN
Contiene únicamente las versiones estables de cada sprint y los tags asociados a las entregas.

### PRODUCTION
Contiene exclusivamente versiones publicadas provenientes de la rama MAIN.

### DEVELOPMENT
Rama principal de desarrollo e integración del proyecto. Todas las nuevas funcionalidades se integran aquí antes de pasar a MAIN.

---

## Metodología de trabajo

1. Los cambios se suben en DEVELOPMENT mediante Pull Requests.
2. DEVELOPMENT se fusiona en MAIN al finalizar cada sprint.
3. MAIN se publica en PRODUCTION cuando la versión es estable.

---

## Sprint Actual

**Sprint 3: dashboards por rol**

- Panel propio para Vecino, Propietario y Autoridad, con gráficos.
- Sensores de ruido y aforo.
- Base de datos SQLite con el historial previo de los sensores.
- Datos manejados con listas de nodos enlazados.

### Cómo ejecutarlo

```bash
python -m pip install -r requirements.txt
python main.py
python -m unittest tests.pruebas   # pruebas automáticas
```

Usuarios de prueba: `usuarios_prueba.txt`. Documentación: carpeta `docs`.


---

## Tecnologías

- Python 3
- [Flet](https://flet.dev/) (interfaz gráfica responsive)
- Base de datos SQLite (datos iniciales en JSON)
- Arquitectura Modelo-Vista-Controlador (MVC)
- Git y GitHub
- Metodología Scrum

