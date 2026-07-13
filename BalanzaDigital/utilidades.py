# ==========================================
# utilidades.py
# Manejo de archivos CSV y persistencia de ventas en formato BI de precios
# ==========================================

import os
import pandas as pd
from datetime import datetime

ARCHIVO = "ventas.csv"


def crear_archivo():
    """
    Crea el archivo ventas.csv si no existe con las columnas del reporte de precios de Lima.
    """
    columnas = [
        "Fecha",
        "Productos",
        "Unidad de medida (Mayorista)",
        "Equiv. (kg./lt) (Mayorista)",
        "Mayorista - Precio Min.",
        "Mayorista - Precio Prom.",
        "Mayorista - Precio Max.",
        "Unidad de medida (Minorista)",
        "Equiv. (kg./lt) (Minorista)",
        "Minorista - Precio Min.",
        "Minorista - Precio Prom.",
        "Minorista - Precio Max."
    ]

    if not os.path.exists(ARCHIVO):
        df = pd.DataFrame(columns=columnas)
        df.to_csv(ARCHIVO, index=False)
    else:
        # Si existe pero es el formato antiguo, lo recreamos
        try:
            df = pd.read_csv(ARCHIVO)
            if "Productos" not in df.columns:
                df_new = pd.DataFrame(columns=columnas)
                df_new.to_csv(ARCHIVO, index=False)
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
    
    # Importación perezosa para evitar dependencias circulares
    from productos import PRODUCTOS_DB
    info = PRODUCTOS_DB.get(producto, {
        "precio_minorista": 2.50,
        "precio_mayorista": 1.60,
        "unidad_mayorista": "Saco",
        "equiv_mayorista": 50.0
    })

    # Extraer variables del producto
    u_may = info.get("unidad_mayorista", "Saco")
    eq_may = info.get("equiv_mayorista", 50.0)
    u_min = "Kilogramo"
    eq_min = 1.0

    # Lógica de asignación de precios para el reporte
    if canal == "Mayorista":
        # La transacción actual define los precios mayoristas
        may_prom = precio
        may_min = round(precio * 0.95, 2)
        may_max = round(precio * 1.05, 2)
        
        # Minorista toma el precio por defecto del producto
        min_prom = info.get("precio_minorista", 2.50)
        min_min = round(min_prom * 0.95, 2)
        min_max = round(min_prom * 1.05, 2)
    else:
        # La transacción actual define los precios minoristas
        min_prom = precio
        min_min = round(precio * 0.95, 2)
        min_max = round(precio * 1.05, 2)
        
        # Mayorista toma el precio por defecto del producto
        may_prom = info.get("precio_mayorista", 1.60)
        may_min = round(may_prom * 0.95, 2)
        may_max = round(may_prom * 1.05, 2)

    venta = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Productos": producto,
        "Unidad de medida (Mayorista)": u_may,
        "Equiv. (kg./lt) (Mayorista)": eq_may,
        "Mayorista - Precio Min.": may_min,
        "Mayorista - Precio Prom.": may_prom,
        "Mayorista - Precio Max.": may_max,
        "Unidad de medida (Minorista)": u_min,
        "Equiv. (kg./lt) (Minorista)": eq_min,
        "Minorista - Precio Min.": min_min,
        "Minorista - Precio Prom.": min_prom,
        "Minorista - Precio Max.": min_max
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