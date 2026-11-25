"""Punto de entrada de la aplicación. Para ejecutarla: python main.py"""
import flet as ft

# App decide qué pantalla se ve en cada momento (ver src/app.py).
from src.app import App


def main(page):
    App(page).ir_a_login()


ft.run(main)
