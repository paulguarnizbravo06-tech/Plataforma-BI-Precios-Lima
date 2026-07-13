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


def enviar_datos_supabase(db_url):
    """
    Sincroniza todos los registros de ventas.csv con la tabla ventas_balanza en Supabase.
    """
    import sqlalchemy
    from sqlalchemy import text
    import pandas as pd
    
    if not os.path.exists(ARCHIVO):
        return False, "No hay datos locales para enviar."
        
    try:
        # Reemplazar cualquier variante de postgresql/psycopg2 con pg8000
        for prefix in ["postgresql+psycopg2://", "postgresql://", "postgres://"]:
            if db_url.startswith(prefix):
                db_url = db_url.replace(prefix, "postgresql+pg8000://", 1)
                break
            
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        engine = sqlalchemy.create_engine(
            db_url,
            connect_args={"ssl_context": ssl_context},
            pool_pre_ping=True
        )
        
        df = pd.read_csv(ARCHIVO, sep=";")
        if df.empty:
            return True, "No hay registros en el historial."
            
        inserted = 0
        with engine.begin() as conn:
            # Crear la tabla si no existe (robusto para el usuario)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ventas_balanza (
                    id SERIAL PRIMARY KEY,
                    fecha TIMESTAMP NOT NULL,
                    producto VARCHAR(100) NOT NULL,
                    unidad_medida_mayorista VARCHAR(50),
                    equiv_kg_lt_mayorista NUMERIC,
                    mayorista_precio_min NUMERIC,
                    mayorista_precio_prom NUMERIC,
                    mayorista_precio_max NUMERIC,
                    unidad_medida_minorista VARCHAR(50),
                    equiv_kg_lt_minorista NUMERIC,
                    minorista_precio_min NUMERIC,
                    minorista_precio_prom NUMERIC,
                    minorista_precio_max NUMERIC,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_fecha_producto UNIQUE (fecha, producto)
                )
            """))
            
            for _, row in df.iterrows():
                # Formatear fecha
                raw_fecha = str(row["Fecha"])
                try:
                    fecha_parsed = datetime.strptime(raw_fecha, "%d/%m/%Y %H:%M:%S")
                except ValueError:
                    try:
                        fecha_parsed = datetime.strptime(raw_fecha, "%d/%m/%Y")
                    except ValueError:
                        continue
                
                # Reemplazar NaN por None
                params = {
                    "fecha": fecha_parsed,
                    "producto": str(row["Productos"]),
                    "u_may": None if pd.isna(row["Unidad de medida (Mayorista)"]) else str(row["Unidad de medida (Mayorista)"]),
                    "eq_may": None if pd.isna(row["Equiv. (kg./lt) (Mayorista)"]) else float(row["Equiv. (kg./lt) (Mayorista)"]),
                    "may_min": None if pd.isna(row["Mayorista - Precio Min."]) else float(row["Mayorista - Precio Min."]),
                    "may_prom": None if pd.isna(row["Mayorista - Precio Prom."]) else float(row["Mayorista - Precio Prom."]),
                    "may_max": None if pd.isna(row["Mayorista - Precio Max."]) else float(row["Mayorista - Precio Max."]),
                    "u_min": None if pd.isna(row["Unidad de medida (Minorista)"]) else str(row["Unidad de medida (Minorista)"]),
                    "eq_min": None if pd.isna(row["Equiv. (kg./lt) (Minorista)"]) else float(row["Equiv. (kg./lt) (Minorista)"]),
                    "min_min": None if pd.isna(row["Minorista - Precio Min."]) else float(row["Minorista - Precio Min."]),
                    "min_prom": None if pd.isna(row["Minorista - Precio Prom."]) else float(row["Minorista - Precio Prom."]),
                    "min_max": None if pd.isna(row["Minorista - Precio Max."]) else float(row["Minorista - Precio Max."])
                }
                
                # Ejecutar INSERT ... ON CONFLICT
                conn.execute(text("""
                    INSERT INTO ventas_balanza (
                        fecha, producto, 
                        unidad_medida_mayorista, equiv_kg_lt_mayorista, 
                        mayorista_precio_min, mayorista_precio_prom, mayorista_precio_max, 
                        unidad_medida_minorista, equiv_kg_lt_minorista, 
                        minorista_precio_min, minorista_precio_prom, minorista_precio_max
                    ) VALUES (
                        :fecha, :producto, 
                        :u_may, :eq_may, 
                        :may_min, :may_prom, :may_max, 
                        :u_min, :eq_min, 
                        :min_min, :min_prom, :min_max
                    ) ON CONFLICT (fecha, producto) DO UPDATE SET
                        unidad_medida_mayorista = EXCLUDED.unidad_medida_mayorista,
                        equiv_kg_lt_mayorista = EXCLUDED.equiv_kg_lt_mayorista,
                        mayorista_precio_min = EXCLUDED.mayorista_precio_min,
                        mayorista_precio_prom = EXCLUDED.mayorista_precio_prom,
                        mayorista_precio_max = EXCLUDED.mayorista_precio_max,
                        unidad_medida_minorista = EXCLUDED.unidad_medida_minorista,
                        equiv_kg_lt_minorista = EXCLUDED.equiv_kg_lt_minorista,
                        minorista_precio_min = EXCLUDED.minorista_precio_min,
                        minorista_precio_prom = EXCLUDED.minorista_precio_prom,
                        minorista_precio_max = EXCLUDED.minorista_precio_max
                """), params)
                inserted += 1
                
        return True, f"Sincronizados {inserted} registros exitosamente con Supabase."
    except Exception as e:
        return False, f"Error al conectar/sincronizar: {e}"