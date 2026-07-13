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
        df.to_csv(ARCHIVO, index=False, sep=";")
    else:
        try:
            df = pd.read_csv(ARCHIVO, sep=";")
            if "Productos" not in df.columns:
                df_new = pd.DataFrame(columns=columnas)
                df_new.to_csv(ARCHIVO, index=False, sep=";")
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
        
        # Minorista se deja vacío en esta transacción (a menos que se autocomplete)
        min_prom = None
        min_min = None
        min_max = None
    else:
        # La transacción actual define los precios minoristas
        min_prom = precio
        min_min = round(precio * 0.95, 2)
        min_max = round(precio * 1.05, 2)
        
        # Mayorista se deja vacío en esta transacción (a menos que se autocomplete)
        may_prom = None
        may_min = None
        may_max = None

    current_day = datetime.now().strftime("%d/%m/%Y")
    
    df = pd.read_csv(ARCHIVO, sep=";")
    
    # Asegurar tipo object para columnas de texto (evita errores de tipo en pandas si están vacías)
    for col in ["Productos", "Unidad de medida (Mayorista)", "Unidad de medida (Minorista)"]:
        if col in df.columns:
            df[col] = df[col].astype(object)
            
    merged = False
    
    # Buscar si hoy ya existe un registro del mismo producto con la columna contraria vacía
    for idx, row in df.iterrows():
        row_date = str(row.get("Fecha", ""))
        row_prod = str(row.get("Productos", ""))
        
        if row_date.startswith(current_day) and row_prod == producto:
            if canal == "Mayorista" and pd.isna(row.get("Mayorista - Precio Prom.")):
                df.at[idx, "Unidad de medida (Mayorista)"] = u_may
                df.at[idx, "Equiv. (kg./lt) (Mayorista)"] = eq_may
                df.at[idx, "Mayorista - Precio Min."] = may_min
                df.at[idx, "Mayorista - Precio Prom."] = may_prom
                df.at[idx, "Mayorista - Precio Max."] = may_max
                merged = True
                break
            elif canal == "Minorista" and pd.isna(row.get("Minorista - Precio Prom.")):
                df.at[idx, "Unidad de medida (Minorista)"] = u_min
                df.at[idx, "Equiv. (kg./lt) (Minorista)"] = eq_min
                df.at[idx, "Minorista - Precio Min."] = min_min
                df.at[idx, "Minorista - Precio Prom."] = min_prom
                df.at[idx, "Minorista - Precio Max."] = min_max
                merged = True
                break
                
    if not merged:
        # Si no se pudo combinar con un registro del mismo día, se agrega uno nuevo
        nueva_venta = pd.DataFrame([{
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Productos": producto,
            "Unidad de medida (Mayorista)": u_may if canal == "Mayorista" else None,
            "Equiv. (kg./lt) (Mayorista)": eq_may if canal == "Mayorista" else None,
            "Mayorista - Precio Min.": may_min,
            "Mayorista - Precio Prom.": may_prom,
            "Mayorista - Precio Max.": may_max,
            "Unidad de medida (Minorista)": u_min if canal == "Minorista" else None,
            "Equiv. (kg./lt) (Minorista)": eq_min if canal == "Minorista" else None,
            "Minorista - Precio Min.": min_min,
            "Minorista - Precio Prom.": min_prom,
            "Minorista - Precio Max.": min_max
        }])
        df = pd.concat([df, nueva_venta], ignore_index=True)
        
    df.to_csv(ARCHIVO, index=False, sep=";")


def obtener_historial():
    crear_archivo()
    return pd.read_csv(ARCHIVO, sep=";")


def ultima_venta():
    crear_archivo()
    historial = pd.read_csv(ARCHIVO, sep=";")

    if len(historial) == 0:
        return None

    return historial.iloc[-1]