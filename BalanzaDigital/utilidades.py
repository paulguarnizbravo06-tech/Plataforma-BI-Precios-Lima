# ==========================================
# utilidades.py
# Manejo de archivos CSV y persistencia de ventas
# ==========================================

import os
import pandas as pd
from datetime import datetime

ARCHIVO = "ventas.csv"


def crear_archivo():
    """
    Crea el archivo ventas.csv si no existe, o migra las columnas si es necesario.
    """
    columnas = [
        "Fecha",
        "Mercado",
        "Canal",
        "Producto",
        "Peso (kg)",
        "Precio/kg",
        "Total"
    ]

    if not os.path.exists(ARCHIVO):
        df = pd.DataFrame(columns=columnas)
        df.to_csv(ARCHIVO, index=False)
    else:
        # Migración automática si falta la columna Canal
        try:
            df = pd.read_csv(ARCHIVO)
            if "Canal" not in df.columns:
                df.insert(2, "Canal", "Minorista") # Añadir columna con valor por defecto
                df.to_csv(ARCHIVO, index=False)
        except Exception as e:
            print(f"Error al verificar/migrar CSV: {e}")


def registrar_venta(
        mercado,
        canal,
        producto,
        peso,
        precio,
        total
):
    crear_archivo()

    venta = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Mercado": mercado,
        "Canal": canal,
        "Producto": producto,
        "Peso (kg)": peso,
        "Precio/kg": precio,
        "Total": total
    }])

    historial = pd.read_csv(ARCHIVO)

    historial = pd.concat(
        [historial, venta],
        ignore_index=True
    )

    historial.to_csv(
        ARCHIVO,
        index=False
    )


def obtener_historial():
    crear_archivo()
    return pd.read_csv(ARCHIVO)


def ultima_venta():
    crear_archivo()
    historial = pd.read_csv(ARCHIVO)

    if len(historial) == 0:
        return None

    return historial.iloc[-1]