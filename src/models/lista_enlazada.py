"""MODELO: LISTA DE NODOS ENLAZADOS.

Es la estructura con la que el programa maneja TODOS los datos en memoria
(usuarios, locales, sensores, historial, incidencias...).

Cada dato va dentro de un "nodo". Cada nodo sabe cuál es el siguiente y cuál
es el anterior, como los vagones de un tren:

    primero -> [dato] <-> [dato] <-> [dato] <- ultimo

Los métodos __iter__, __len__ y __reversed__ son nombres especiales de Python:
gracias a ellos se puede usar "for", "len()", "in" y "reversed()" con la lista.
"""


class Nodo:
    def __init__(self, dato):
        # Lo que guarda el nodo (un diccionario, un usuario, un local...).
        self.dato = dato
        # Todavía no está unido a ningún otro nodo.
        self.anterior = None
        self.siguiente = None


class ListaEnlazada:
    def __init__(self, datos=()):
        # La lista empieza vacía.
        self.primero = None
        self.ultimo = None
        self.cantidad = 0
        # Si nos dan datos, los vamos añadiendo uno a uno.
        for dato in datos:
            self.append(dato)

    def append(self, dato):
        """Añade un dato al final."""
        nodo = Nodo(dato)
        if self.ultimo is None:
            # Lista vacía: el nodo nuevo es el primero y el último a la vez.
            self.primero = nodo
        else:
            # Lo enganchamos detrás del que era el último.
            nodo.anterior = self.ultimo
            self.ultimo.siguiente = nodo
        self.ultimo = nodo
        self.cantidad = self.cantidad + 1

    def insertar_inicio(self, dato):
        """Añade un dato al principio."""
        nodo = Nodo(dato)
        if self.primero is None:
            self.ultimo = nodo
        else:
            nodo.siguiente = self.primero
            self.primero.anterior = nodo
        self.primero = nodo
        self.cantidad = self.cantidad + 1

    def eliminar(self, condicion):
        """Quita todos los datos que cumplen la condición. Devuelve cuántos ha quitado.

        "condicion" es una función que recibe un dato y devuelve True o False.
        """
        quitados = 0
        nodo = self.primero
        while nodo is not None:
            if condicion(nodo.dato):
                # Unimos el nodo anterior con el siguiente, saltándonos este.
                if nodo.anterior is None:
                    self.primero = nodo.siguiente
                else:
                    nodo.anterior.siguiente = nodo.siguiente
                if nodo.siguiente is None:
                    self.ultimo = nodo.anterior
                else:
                    nodo.siguiente.anterior = nodo.anterior
                quitados = quitados + 1
            nodo = nodo.siguiente
        self.cantidad = self.cantidad - quitados
        return quitados

    def buscar(self, condicion):
        """Devuelve el primer dato que cumple la condición, o None si no hay ninguno."""
        for dato in self:
            if condicion(dato):
                return dato
        return None

    def filtrar(self, condicion):
        """Devuelve otra lista enlazada solo con los datos que cumplen la condición."""
        resultado = ListaEnlazada()
        for dato in self:
            if condicion(dato):
                resultado.append(dato)
        return resultado

    def ultimos(self, maximo=None):
        """Lista normal de Python con los últimos datos, del más nuevo al más antiguo."""
        resultado = []
        for dato in reversed(self):
            if maximo is not None and len(resultado) == maximo:
                break
            resultado.append(dato)
        return resultado

    def __iter__(self):
        # Recorre del primero al último. "yield" entrega los datos de uno en uno.
        nodo = self.primero
        while nodo is not None:
            yield nodo.dato
            nodo = nodo.siguiente

    def __reversed__(self):
        # Recorre al revés: del último al primero.
        nodo = self.ultimo
        while nodo is not None:
            yield nodo.dato
            nodo = nodo.anterior

    def __len__(self):
        return self.cantidad
