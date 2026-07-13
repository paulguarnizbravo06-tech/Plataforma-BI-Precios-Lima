# ==========================================
# balanza.py
# Simulación del sensor de peso IoT
# ==========================================

import random
import time


class Balanza:

    def __init__(self):
        self.peso = 0.0

    def pesar(self):
        """
        Simula el pesaje de un producto.
        Devuelve el peso final.
        """

        peso_final = round(random.uniform(0.50, 8.00), 3)

        return peso_final


    def animacion(self, callback=None):
        """
        Simula cómo aumenta el peso poco a poco.
        callback recibe el peso para actualizar la interfaz.
        """

        peso_final = self.pesar()

        peso = 0.0

        while peso < peso_final:

            incremento = round(random.uniform(0.10, 0.40), 3)

            peso += incremento

            if peso > peso_final:
                peso = peso_final

            if callback:
                callback(round(peso,3))

            time.sleep(0.08)

        self.peso = peso_final

        return peso_final


    def calcular_total(self, precio_kg):

        return round(self.peso * precio_kg, 2)