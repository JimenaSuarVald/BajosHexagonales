"""PRUEBAS automáticas. Para ejecutarlas, desde la carpeta del proyecto:

    python -m unittest tests.pruebas

Cada prueba trabaja con una base de datos nueva en una carpeta temporal: la
base de datos y los JSON reales de src/models NO se tocan.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace

from src.app import App
from src.controllers.sensor_controller import COLORES, fecha_actual
from src.models import base_datos, sensor
from src.models.lista_enlazada import ListaEnlazada
from src.models.local import cargar_locales, simplificar_calle
from src.models.usuario import Usuario, cargar_usuarios
from src.views.bar_sensores_view import BarSensoresView
from src.views.panel_sensores_view import PanelSensoresView
from src.views.piezas_sensores import grafico_barras, grafico_lineas

MOTIVO = "Ruido muy por encima del límite durante toda la noche."


class PaginaFalsa:
    """Hace de ventana de Flet: guarda lo último que se ha enseñado."""

    width = 400
    title = theme_mode = dialogo = None

    def clean(self):
        self.pantalla = None

    def add(self, pantalla):
        self.pantalla = pantalla

    def update(self):
        pass

    def show_dialog(self, dialogo):
        self.dialogo = dialogo

    def pop_dialog(self):
        self.dialogo = None


def textos(control):
    """Todos los textos que hay dentro de una pantalla, en uno solo."""
    partes = []
    for nombre in ("value", "label", "tooltip"):
        valor = getattr(control, nombre, None)
        if isinstance(valor, str):
            partes.append(valor)
    for nombre in ("content", "controls", "rows", "cells", "columns"):
        valor = getattr(control, nombre, None)
        if isinstance(valor, str):
            partes.append(valor)
        elif isinstance(valor, (list, tuple)):
            for hijo in valor:
                partes.append(textos(hijo))
        elif valor is not None:
            partes.append(textos(valor))
    return " | ".join(partes)


class ConDatosTemporales(unittest.TestCase):
    def setUp(self):
        # La base de datos se crea en una carpeta temporal vacía.
        self.temporal = tempfile.TemporaryDirectory()
        self.carpeta_real = base_datos.CARPETA
        base_datos.CARPETA = self.temporal.name
        self.escribir("ids_policiales.json", ["POL-0001", "POL-0002"])
        self.datos_iniciales()
        self.app = App(PaginaFalsa())
        self.sensores = self.app.sensor_controller
        self.vigilancia = self.app.vigilancia_controller
        self.locales = self.app.local_controller
        self.login = self.app.login_controller
        # Un usuario de prueba por rol.
        self.vecino = self.login.users.buscar_por_email("vecino@arguelles.es")
        self.dueno = self.login.users.buscar_por_email("bar@arguelles.es")
        self.policia = self.login.users.buscar_por_email("ayto@arguelles.es")

    def tearDown(self):
        base_datos.CARPETA = self.carpeta_real
        self.temporal.cleanup()

    def datos_iniciales(self):
        """JSON que habrá en la carpeta antes de crear la base de datos (ninguno más)."""

    def escribir(self, nombre, datos):
        """Escribe un JSON inicial en la carpeta temporal."""
        with open(os.path.join(self.temporal.name, nombre), "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo)

    def poner_valor(self, codigo, tipo, valor):
        """Cambia el valor actual de un sensor (añade una medida nueva)."""
        actual = sensor.sensores_actuales(codigo).buscar(lambda s: s["tipo"] == tipo)
        sensor.insertar_medida(actual["id"], valor, fecha_actual())

    def pantalla(self, usuario):
        """Textos del panel principal de un usuario."""
        self.app.usuario = usuario
        self.app.ir_a_principal()
        return textos(self.app.page.pantalla)


class PruebasListaEnlazada(unittest.TestCase):
    def test_vacia(self):
        lista = ListaEnlazada()
        self.assertEqual((len(lista), list(lista), lista.ultimos(3)), (0, [], []))
        self.assertFalse(lista)
        self.assertIsNone(lista.buscar(lambda x: True))
        self.assertEqual(lista.eliminar(lambda x: True), 0)

    def test_anadir_y_recorrer(self):
        lista = ListaEnlazada([2, 3])
        lista.append(4)
        lista.insertar_inicio(1)
        self.assertEqual(list(lista), [1, 2, 3, 4])
        self.assertEqual(list(reversed(lista)), [4, 3, 2, 1])
        self.assertEqual(lista.ultimos(2), [4, 3])
        self.assertIn(3, lista)

    def test_insertar_inicio_en_vacia(self):
        lista = ListaEnlazada()
        lista.insertar_inicio(1)
        lista.append(2)
        self.assertEqual(list(reversed(lista)), [2, 1])

    def test_eliminar_en_cada_posicion(self):
        # (dato que se borra, lo que debe quedar)
        for borrar, queda in ((1, [2, 3]), (2, [1, 3]), (3, [1, 2]), (9, [1, 2, 3])):
            lista = ListaEnlazada([1, 2, 3])
            lista.eliminar(lambda x: x == borrar)
            self.assertEqual(list(lista), queda)
            self.assertEqual(list(reversed(lista)), queda[::-1])
            self.assertEqual(len(lista), len(queda))

    def test_eliminar_todos_y_seguir(self):
        lista = ListaEnlazada([1, 1])
        self.assertEqual(lista.eliminar(lambda x: True), 2)
        lista.append(5)
        self.assertEqual((list(lista), list(reversed(lista))), ([5], [5]))

    def test_filtrar(self):
        pares = ListaEnlazada([1, 2, 3, 4]).filtrar(lambda x: x % 2 == 0)
        self.assertIsInstance(pares, ListaEnlazada)
        self.assertEqual(list(pares), [2, 4])


class PruebasBaseDeDatos(ConDatosTemporales):
    def test_tablas_e_indices(self):
        nombres = [f["name"] for f in base_datos.consultar("SELECT name FROM sqlite_master")]
        for nombre in ("locales", "usuarios", "ids_policiales", "sensores", "medidas", "incidencias",
                       "cierres", "notificaciones", "medidas_por_sensor", "un_cierre_activo"):
            self.assertIn(nombre, nombres)

    def test_devuelve_listas_enlazadas(self):
        self.assertIsInstance(base_datos.consultar("SELECT * FROM locales"), ListaEnlazada)
        self.assertIsInstance(cargar_locales(), ListaEnlazada)
        self.assertIsInstance(cargar_usuarios(), ListaEnlazada)

    def test_claves_ajenas(self):
        # Un sensor de un local que no existe no se puede guardar.
        with self.assertRaises(sqlite3.IntegrityError):
            sensor.insertar_sensor("NEG-999", "ruido")
        # Ni un usuario con un ID policial que no está en la lista oficial.
        with self.assertRaises(sqlite3.IntegrityError):
            self.login.users.crear_usuario("X", "x@x.es", "1234", "Autoridad", id_policial="POL-9999")

    def test_transaccion_todo_o_nada(self):
        antes = len(self.vigilancia.incidencias_de("NEG-001"))
        with self.assertRaises(sqlite3.IntegrityError):
            with base_datos.transaccion():
                self.vigilancia.apuntar_incidencia("NEG-001", "Prueba", "Yo", "Se tiene que deshacer")
                sensor.insertar_sensor("NEG-999", "ruido")
        self.assertEqual(len(self.vigilancia.incidencias_de("NEG-001")), antes)

    def test_un_solo_cierre_activo_por_local(self):
        self.vigilancia.cerrar_local(self.policia, "NEG-001", MOTIVO)
        with self.assertRaises(sqlite3.IntegrityError):
            base_datos.insertar("cierres", {"local": "NEG-001", "fecha": "x", "policia": "x", "motivo": "x"})

    def test_texto_con_sql_se_guarda_tal_cual(self):
        texto = "Robert'); DROP TABLE locales; --"
        self.assertEqual(self.login.users.cambiar_calle(self.vecino, texto), "")
        self.assertEqual(self.login.users.buscar_por_email("vecino@arguelles.es").calle, texto)
        self.assertIsNotNone(self.locales.buscar("NEG-001"))

    def test_sin_json_crea_los_datos_de_prueba(self):
        self.assertEqual([l.codigo for l in cargar_locales()], ["NEG-001"])
        self.assertEqual(len(cargar_usuarios()), 3)
        self.assertEqual(len(self.sensores.sensores_de("NEG-001")), 5)


class PruebasImportarJson(ConDatosTemporales):
    def datos_iniciales(self):
        self.escribir("locales.json", [
            {"codigo": "NEG-001", "nombre": "Bar Demo", "direccion": "Calle Ferraz 10", "tipo": "Bar", "aforo": 80},
            {"codigo": "NEG-003", "nombre": "Otro", "direccion": "C/Gato 1", "tipo": "Bar", "aforo": 50},
        ])
        # Usuarios del Sprint 1 y 2: sin calle, con "" en vez de NULL y con un local que ya no existe.
        self.escribir("usuarios.json", [
            {"nombre": "V", "email": "vecino@arguelles.es", "rol": "Vecino", "password_hash": "h",
             "codigo_negocio": "", "id_policial": ""},
            {"nombre": "P", "email": "bar@arguelles.es", "rol": "Propietario", "password_hash": "h",
             "codigo_negocio": "NEG-001", "id_policial": ""},
            {"nombre": "A", "email": "ayto@arguelles.es", "rol": "Autoridad", "password_hash": "h",
             "codigo_negocio": "", "id_policial": "POL-0001"},
            {"nombre": "Q", "email": "q@a.es", "rol": "Propietario", "password_hash": "h",
             "codigo_negocio": "NEG-777", "id_policial": ""},
        ])
        self.escribir("sensores.json", [
            {"local": "NEG-001", "tipo": "temperatura", "valor": 25.0, "fecha": "2026-11-13 17:51"},
            {"local": "NEG-777", "tipo": "temperatura", "valor": 1.0, "fecha": "2026-11-13 17:51"},
        ])
        self.escribir("historial_sensores.json", [
            {"local": "NEG-001", "tipo": "temperatura", "valor": 20.0, "fecha": "2026-11-12 17:51"},
            {"local": "NEG-001", "tipo": "temperatura", "valor": 25.0, "fecha": "2026-11-13 17:51"},
            {"local": "NEG-777", "tipo": "temperatura", "valor": 1.0, "fecha": "2026-11-13 17:51"},
        ])
        self.escribir("incidencias.json", [
            {"local": "NEG-001", "fecha": "2026-11-12 23:51", "tipo": "Nivel peligroso",
             "autor": "Sistema de sensores", "descripcion": "x"},
        ])
        self.escribir("notificaciones.json", [
            {"para": "Autoridad", "fecha": "2026-11-12 23:51", "titulo": "t", "mensaje": "m", "leida": False},
            {"para": "NEG-777", "fecha": "2026-11-12 23:51", "titulo": "t", "mensaje": "m", "leida": False},
        ])

    def test_importa_el_historial_previo(self):
        medidas = self.sensores.historial_de("NEG-001", "temperatura", 10)
        self.assertEqual([m["valor"] for m in medidas], [25.0, 20.0])
        self.assertEqual(self.sensores.valor("NEG-001", "temperatura"), 25.0)
        # Los valores sin decimales vuelven como enteros (58 y no 58.0).
        self.poner_valor("NEG-001", "aforo", 58.0)
        self.assertEqual(repr(self.sensores.valor("NEG-001", "aforo")), "58")
        # Los demás sensores y el otro local reciben su historial inventado.
        self.assertEqual(len(self.sensores.sensores_de("NEG-001")), 5)
        self.assertEqual(len(self.sensores.historial_de("NEG-003", "ruido", 100)), 25)

    def test_importa_usuarios_antiguos_y_avisos(self):
        self.assertEqual(self.dueno.codigo_negocio, "NEG-001")
        self.assertEqual(self.policia.id_policial, "POL-0001")
        self.assertEqual(self.vecino.calle, "")
        self.assertEqual(self.login.users.buscar_por_email("q@a.es").codigo_negocio, "")
        self.assertEqual(len(self.vigilancia.incidencias_de("NEG-001")), 1)
        self.assertEqual(self.vigilancia.sin_leer(self.policia), 1)

    def test_solo_se_importa_una_vez(self):
        self.escribir("locales.json", [])
        base_datos.preparar()
        self.assertEqual(len(cargar_locales()), 2)

    def test_json_danado_no_deja_base_de_datos_a_medias(self):
        base_datos.CARPETA = tempfile.mkdtemp(dir=self.temporal.name)
        with open(os.path.join(base_datos.CARPETA, "cierres.json"), "w", encoding="utf-8") as archivo:
            archivo.write("[{")
        with self.assertRaises(ValueError):
            base_datos.preparar()
        self.assertIsNone(base_datos.consultar_uno("SELECT name FROM sqlite_master WHERE name = 'medidas'"))


class PruebasSensores(ConDatosTemporales):
    def test_umbrales(self):
        # (tipo, valor, color esperado). El Bar Demo tiene un aforo de 80.
        casos = [
            ("temperatura", 27, "verde"), ("temperatura", 27.1, "amarillo"),
            ("temperatura", 30, "amarillo"), ("temperatura", 30.1, "rojo"),
            ("humedad", 29.9, "rojo"), ("humedad", 30, "amarillo"), ("humedad", 34.9, "amarillo"),
            ("humedad", 35, "verde"), ("humedad", 65, "verde"), ("humedad", 70, "amarillo"),
            ("humedad", 70.1, "rojo"),
            ("calidad_aire", 799, "verde"), ("calidad_aire", 800, "amarillo"),
            ("calidad_aire", 1199, "amarillo"), ("calidad_aire", 1200, "rojo"),
            ("ruido", 65, "verde"), ("ruido", 65.1, "amarillo"), ("ruido", 80, "amarillo"), ("ruido", 80.1, "rojo"),
            ("aforo", 64, "verde"), ("aforo", 65, "amarillo"), ("aforo", 80, "amarillo"), ("aforo", 81, "rojo"),
        ]
        for tipo, valor, color in casos:
            self.assertEqual(self.sensores.color_sensor("NEG-001", tipo, valor), color, (tipo, valor))

    def test_todos_los_bares_tienen_todos_los_sensores(self):
        self.assertEqual([s["tipo"] for s in self.sensores.sensores_de("NEG-001")], sensor.TIPOS_SENSOR)

    def test_bar_antiguo_recibe_los_sensores_nuevos(self):
        base_datos.ejecutar("DELETE FROM sensores WHERE tipo IN ('ruido', 'aforo')")
        self.sensores.medir_todos()
        self.assertEqual(len(self.sensores.sensores_de("NEG-001")), 5)

    def test_leds_y_ventilador(self):
        for tipo, valor in (("temperatura", 31), ("humedad", 50), ("calidad_aire", 500)):
            self.poner_valor("NEG-001", tipo, valor)
        self.assertEqual(self.sensores.leds("NEG-001"), {"rojo": True, "azul": False, "verde": False})
        self.assertFalse(self.sensores.ventilador("NEG-001"))
        self.poner_valor("NEG-001", "calidad_aire", 1300)
        self.assertTrue(self.sensores.ventilador("NEG-001"))

    def test_color_bar_es_el_peor(self):
        for tipo, valor in (("temperatura", 20), ("humedad", 50), ("calidad_aire", 500), ("ruido", 50), ("aforo", 10)):
            self.poner_valor("NEG-001", tipo, valor)
        self.assertEqual(self.sensores.color_bar("NEG-001"), "verde")
        self.poner_valor("NEG-001", "ruido", 70)
        self.assertEqual(self.sensores.color_bar("NEG-001"), "amarillo")
        self.poner_valor("NEG-001", "aforo", 90)
        self.assertEqual(self.sensores.color_bar("NEG-001"), "rojo")

    def test_medir_guarda_todo_el_historial(self):
        for _ in range(3):
            self.app.medir()
        self.assertEqual(len(self.sensores.historial_de("NEG-001", "ruido", 1000)), 28)

    def test_historial_y_estadisticas(self):
        medidas = self.sensores.historial_de("NEG-001", "ruido", 24)
        self.assertEqual(len(medidas), 24)
        self.assertEqual(medidas[0]["fecha"][:10], fecha_actual()[:10])
        self.assertEqual(self.sensores.estadisticas([{"valor": 1}, {"valor": 2}, {"valor": 6}]), (1, 3.0, 6))
        self.assertIsNone(self.sensores.estadisticas([]))

    def test_simular_solo_autoridad(self):
        for usuario in (self.vecino, self.dueno):
            self.assertNotEqual(self.sensores.simular(usuario, "NEG-001", "alerta"), "")
            self.assertEqual(self.sensores.escenario("NEG-001"), "normal")
        self.assertEqual(self.sensores.simular(self.policia, "NEG-001", "alerta"), "")
        for _ in range(12):
            self.app.medir()
        self.assertEqual(self.sensores.color_bar("NEG-001"), "rojo")


class PruebasLocales(ConDatosTemporales):
    def crear(self):
        return self.locales.crear(self.policia, "neg-002", "Otro", "C/ Martín de los Heros, nº 3", "Bar", "50")

    def test_local_nuevo_tiene_sensores_desde_el_principio(self):
        self.crear()
        self.assertEqual(len(self.sensores.sensores_de("NEG-002")), 5)
        self.assertGreater(self.sensores.valor("NEG-002", "temperatura"), 0)

    def test_eliminar_borra_tambien_sus_datos(self):
        self.crear()
        self.vigilancia.cerrar_local(self.policia, "NEG-002", MOTIVO)
        self.assertEqual(self.locales.eliminar(self.policia, "NEG-002"), "")
        self.assertEqual(len(self.vigilancia.cerrados()), 0)
        for tabla in ("sensores", "incidencias", "cierres", "notificaciones"):
            self.assertEqual(len(base_datos.consultar(f"SELECT * FROM {tabla} WHERE local = 'NEG-002'")), 0)
        huerfanas = "SELECT * FROM medidas WHERE sensor NOT IN (SELECT id FROM sensores)"
        self.assertEqual(len(base_datos.consultar(huerfanas)), 0)
        # El propietario de ese local se queda sin local (NULL), no con un código que no existe.
        self.assertEqual(self.dueno.codigo_negocio, "NEG-001")
        # Los datos de los demás locales siguen ahí.
        self.assertEqual(len(self.sensores.sensores_de("NEG-001")), 5)
        # Y si se vuelve a crear, empieza abierto.
        self.crear()
        self.assertIsNone(self.vigilancia.cierre_activo("NEG-002"))

    def test_permisos(self):
        otro = self.crear()[0]
        suyo = self.locales.buscar("NEG-001")
        # (usuario, puede crear/eliminar, puede ver el suyo, puede ver el otro)
        for usuario, crear, ver_suyo, ver_otro in (
            (self.vecino, False, False, False),
            (self.dueno, False, True, False),
            (self.policia, True, True, True),
        ):
            self.assertEqual(self.locales.puede_crear(usuario), crear)
            self.assertEqual(self.locales.puede_eliminar(usuario), crear)
            self.assertEqual(self.locales.puede_ver_sensores(usuario, suyo), ver_suyo)
            self.assertEqual(self.locales.puede_ver_sensores(usuario, otro), ver_otro)
        self.assertNotEqual(self.locales.eliminar(self.dueno, "NEG-002"), "")
        self.assertIsNotNone(self.locales.buscar("NEG-002"))

    def test_calles(self):
        for texto, esperado in (
            ("Calle Ferraz 10", "ferraz"), ("C/Gato nº0", "gato"), ("c/ Martín de los Heros, nº 3 bajo B", "martin de los heros"),
            ("FERRAZ", "ferraz"), ("Calle 2 de Mayo 5", "2 de mayo"), ("Callejón del Gato 1", "callejon del gato"),
        ):
            self.assertEqual(simplificar_calle(texto), esperado)
        self.assertEqual([l.codigo for l in self.locales.de_calle("ferraz")], ["NEG-001"])
        self.assertEqual(len(self.locales.de_calle("")), 0)


class PruebasAcceso(ConDatosTemporales):
    def registrar(self, email, rol, codigo):
        return self.login.registrar("Ana", email, "1234", "1234", rol, codigo)

    def test_registro_por_rol(self):
        self.assertIsNone(self.registrar("a@a.es", "Vecino", "  ")[0])
        self.assertEqual(self.registrar("a@a.es", "Vecino", " Calle Ferraz ")[0].calle, "Calle Ferraz")
        self.assertIsNone(self.registrar("b@a.es", "Propietario", "NEG-999")[0])
        self.assertIsNone(self.registrar("b@a.es", "Propietario", "NEG-001")[0])  # ya tiene dueño
        self.assertIsNone(self.registrar("c@a.es", "Autoridad", "POL-0001")[0])  # ya usado
        policia = self.registrar("c@a.es", "Autoridad", "pol-0002")[0]
        self.assertEqual((policia.id_policial, policia.calle), ("POL-0002", ""))

    def test_login(self):
        self.assertIsNotNone(self.login.autenticar("VECINO@arguelles.es", "1234")[0])
        self.assertIsNone(self.login.autenticar("vecino@arguelles.es", "mal")[0])

    def test_cambiar_calle(self):
        users = self.login.users
        self.assertEqual(users.cambiar_calle(self.vecino, " Calle Princesa "), "")
        self.assertEqual(users.buscar_por_email(self.vecino.email).calle, "Calle Princesa")
        self.assertNotEqual(users.cambiar_calle(self.vecino, " "), "")
        self.assertNotEqual(users.cambiar_calle(self.dueno, "Calle X"), "")


class PruebasVigilancia(ConDatosTemporales):
    def test_un_solo_aviso_por_alerta(self):
        self.poner_valor("NEG-001", "ruido", 95)
        for _ in range(3):
            self.vigilancia.revisar_alertas(self.sensores)
        self.assertEqual(self.vigilancia.sin_leer(self.policia), 1)
        self.assertTrue(self.vigilancia.alerta_abierta("NEG-001"))
        for tipo, valor in (("temperatura", 20), ("humedad", 50), ("calidad_aire", 500), ("ruido", 50), ("aforo", 10)):
            self.poner_valor("NEG-001", tipo, valor)
        self.vigilancia.revisar_alertas(self.sensores)
        self.assertFalse(self.vigilancia.alerta_abierta("NEG-001"))

    def test_cierre_reclamacion_y_resolucion(self):
        v = self.vigilancia
        self.assertNotEqual(v.cerrar_local(self.dueno, "NEG-001", MOTIVO), "")
        self.assertNotEqual(v.cerrar_local(self.policia, "NEG-001", "corto"), "")
        self.assertEqual(v.cerrar_local(self.policia, "NEG-001", MOTIVO), "")
        self.assertNotEqual(v.cerrar_local(self.policia, "NEG-001", MOTIVO), "")
        self.assertEqual(v.sin_leer(self.dueno), 1)
        self.assertNotEqual(v.reclamar(self.vecino, "NEG-001", "No es justo"), "")
        self.assertEqual(v.reclamar(self.dueno, "NEG-001", "No es justo"), "")
        self.assertNotEqual(v.reclamar(self.dueno, "NEG-001", "Otra vez"), "")
        self.assertEqual(len(v.reclamaciones_pendientes()), 1)
        self.assertNotEqual(v.resolver_reclamacion(self.dueno, "NEG-001", False, "Sí"), "")
        self.assertEqual(v.resolver_reclamacion(self.policia, "NEG-001", False, "Tienes razón"), "")
        self.assertIsNone(v.cierre_activo("NEG-001"))
        self.assertEqual(v.ultimo_cierre("NEG-001")["estado_reclamacion"], "No justificado")
        self.assertEqual(len(v.incidencias_de("NEG-001")), 3)
        self.assertEqual(len(v.todas_las_incidencias("Reclamación", 10)), 1)

    def test_justificado_sigue_cerrado_y_se_reabre(self):
        v = self.vigilancia
        v.cerrar_local(self.policia, "NEG-001", MOTIVO)
        v.reclamar(self.dueno, "NEG-001", "No es justo")
        v.resolver_reclamacion(self.policia, "NEG-001", True, "Está justificado")
        self.assertIsNotNone(v.cierre_activo("NEG-001"))
        self.assertNotEqual(v.reabrir_local(self.vecino, "NEG-001", ""), "")
        self.assertEqual(v.reabrir_local(self.policia, "NEG-001", ""), "")
        self.assertIsNone(v.cierre_activo("NEG-001"))

    def test_marcar_leidas_no_afecta_a_otros(self):
        self.vigilancia.notificar(None, "A", "a")
        self.vigilancia.notificar("NEG-001", "B", "b")
        self.vigilancia.marcar_leidas(self.dueno)
        self.assertEqual(self.vigilancia.sin_leer(self.dueno), 0)
        self.assertEqual(self.vigilancia.sin_leer(self.policia), 1)
        self.assertEqual(self.vigilancia.notificaciones_de(self.vecino), [])


class PruebasPantallas(ConDatosTemporales):
    def test_panel_del_vecino(self):
        texto = self.pantalla(self.vecino)
        self.assertIn("Mi calle: Calle Ferraz", texto)
        self.assertIn("Ruido", texto)
        self.assertIn("Aforo", texto)
        for oculto in ("Temperatura", "Ver sensores", "Notificaciones", "Cerrar temporalmente"):
            self.assertNotIn(oculto, texto)

    def test_vecino_sin_calle_o_sin_bares(self):
        self.vecino.calle = ""
        self.assertIn("Todavía no has indicado tu calle", self.pantalla(self.vecino))
        self.vecino.calle = "Calle Inventada"
        self.assertIn("No hay locales registrados en tu calle", self.pantalla(self.vecino))

    def test_panel_del_propietario(self):
        self.locales.crear(self.policia, "NEG-002", "Ajeno", "Calle X 1", "Bar", "50")
        texto = self.pantalla(self.dueno)
        self.assertIn("Mi local: Bar Demo", texto)
        self.assertIn("Incidencias de mi local", texto)
        # 5 tarjetas con estadísticas (las de su local) y solo un botón de detalle (el suyo).
        self.assertEqual(texto.count("Mínimo"), 5)
        self.assertEqual(texto.count("Ver sensores e incidencias"), 1)
        self.assertNotIn("Resumen de la zona", texto)

    def test_propietario_sin_local(self):
        self.locales.eliminar(self.policia, "NEG-001")
        self.assertIn("ya no está registrado", self.pantalla(self.dueno))

    def test_propietario_cerrado_puede_reclamar(self):
        self.vigilancia.cerrar_local(self.policia, "NEG-001", MOTIVO)
        texto = self.pantalla(self.dueno)
        self.assertIn("Presentar reclamación", texto)
        self.assertIn(MOTIVO, texto)

    def test_panel_de_la_autoridad(self):
        self.poner_valor("NEG-001", "ruido", 95)
        texto = self.pantalla(self.policia)
        for visible in ("Resumen de la zona", "Comparación de bares", "Incidencias de la zona", "Cerrar temporalmente"):
            self.assertIn(visible, texto)

    def test_filtros_y_comparacion(self):
        self.locales.crear(self.policia, "NEG-002", "Zeta", "Calle X 1", "Bar", "50")
        # Valores fijos: de noche el historial inventado trae alertas.
        for tipo, valor in (("temperatura", 20), ("humedad", 50), ("calidad_aire", 500), ("ruido", 50), ("aforo", 10)):
            self.poner_valor("NEG-001", tipo, valor)
        self.poner_valor("NEG-002", "ruido", 95)
        self.app.usuario = self.policia
        panel = PanelSensoresView(self.app)
        panel.construir()
        # El más peligroso, primero.
        self.assertIn("Zeta", textos(panel.lista_bares.controls[0]))
        panel.buscador.value = "neg-001"
        panel.filtrar_bares("evento")
        self.assertEqual(len(panel.lista_bares.controls), 1)
        panel.buscador.value = ""
        for estado in ["todos", "cerrado"] + COLORES:
            panel.estado.value = estado
            panel.filtrar_bares("evento")
        for tipo in sensor.TIPOS_SENSOR:
            panel.tipo.value = tipo
            panel.comparar("evento")
            self.assertIn("Zeta", textos(panel.grafico))
        panel.tipo_incidencia.value = "Reapertura"
        panel.filtrar_incidencias("evento")
        self.assertIn("No hay incidencias", textos(panel.log))

    def test_detalle_del_bar(self):
        bar = self.locales.buscar("NEG-001")
        self.app.usuario = self.policia
        self.assertIn("Simulador", textos(BarSensoresView(self.app, bar).construir()))
        self.app.usuario = self.dueno
        self.assertNotIn("Simulador", textos(BarSensoresView(self.app, bar).construir()))
        # Un vecino no puede abrirlo: la pantalla no cambia.
        self.app.usuario = self.vecino
        self.app.page.pantalla = "la de antes"
        self.app.ir_a_bar(bar)
        self.assertEqual(self.app.page.pantalla, "la de antes")

    def test_resto_de_pantallas(self):
        for usuario in (self.vecino, self.dueno, self.policia):
            self.app.entrar(usuario)
            self.app.ir_a_locales()
            self.assertIn("Bar Demo", textos(self.app.page.pantalla))
            self.app.ir_a_nuevo_local()
            self.app.ir_a_editar_local(self.locales.buscar("NEG-001"))
            self.app.ir_a_registro()
        self.app.ir_a_login()
        self.assertIsNone(self.app.usuario)

    def test_ventanita_de_la_calle(self):
        self.pantalla(self.vecino)
        PanelSensoresView(self.app).pedir_calle(None)
        dialogo = self.app.page.dialogo
        # controls[1] es la caja y actions[1] el botón "Guardar".
        dialogo.actions[1].on_click(None)
        self.assertIsNotNone(self.app.page.dialogo)  # vacía: sigue abierta con el error
        dialogo.content.controls[1].value = "Calle Princesa"
        dialogo.actions[1].on_click(None)
        self.assertIsNone(self.app.page.dialogo)
        self.assertIn("Mi calle: Calle Princesa", textos(self.app.page.pantalla))

    def test_graficos_con_pocos_datos_o_iguales(self):
        limites = {"precaucion": 5, "peligro": 10}
        for valores in ([], [1], [5, 5], [0, 0, 0]):
            medidas = [{"valor": v, "fecha": "2026-11-25 10:00"} for v in valores]
            grafico_lineas(medidas, limites)
        grafico_barras([])
        grafico_barras([("A", 0, "verde")])

    def test_grafico_se_adapta_al_tamano(self):
        medidas = [{"valor": v, "fecha": "2026-11-25 10:00"} for v in (3, 20, 8)]
        lienzo = grafico_lineas(medidas, {"precaucion": 5, "peligro": 10}).controls[0].controls[1]
        lienzo.update = lambda: None
        lienzo.on_resize(SimpleNamespace(width=600, height=130))
        # 2 límites + 2 tramos + 1 punto, todo dentro del lienzo.
        self.assertEqual(len(lienzo.shapes), 5)
        for forma in lienzo.shapes[:4]:
            self.assertTrue(0 <= forma.x1 <= 600 and 0 <= forma.x2 <= 600)
            self.assertTrue(0 <= forma.y1 <= 130 and 0 <= forma.y2 <= 130)


class PruebasDatosAntiguos(ConDatosTemporales):
    def test_autoridad_antigua_sin_id(self):
        # Cuentas del Sprint 1: el panel debe abrirse aunque no tengan ID policial.
        self.assertIn("Resumen", self.pantalla(Usuario("Vieja", "v@a.es", "Autoridad", "x")))


if __name__ == "__main__":
    unittest.main()
