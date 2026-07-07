import numpy as np
import pandas as pd
import pyodbc


class ClaseDB:
    """Conexion y operaciones auxiliares para el Data Warehouse."""

    @staticmethod
    def conectar_sql():
        return pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=DESKTOP-R32DQGB\\SQLEXPRESS;"
            "DATABASE=BI_MERCADOS_LIMA_F;"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;",
            timeout=5
        )

    @staticmethod
    def sql_valor(v):
        """Convierte NaN/NaT a None para que SQL Server reciba NULL."""
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    @staticmethod
    def obtener_o_crear_producto(cursor, producto):
        producto = (producto or "Sin producto").strip()
        cursor.execute("SELECT id_producto FROM DIM_PRODUCTO WHERE producto = ?", producto)
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("""
            INSERT INTO DIM_PRODUCTO (producto)
            OUTPUT INSERTED.id_producto
            VALUES (?)
        """, producto)
        return cursor.fetchone()[0]

    @staticmethod
    def obtener_o_crear_tipo_venta(cursor, tipo_venta):
        tipo_venta = (tipo_venta or "No especificado").strip()
        cursor.execute("SELECT id_tipo_venta FROM DIM_TIPO_VENTA WHERE tipo_venta = ?", tipo_venta)
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("""
            INSERT INTO DIM_TIPO_VENTA (tipo_venta)
            OUTPUT INSERTED.id_tipo_venta
            VALUES (?)
        """, tipo_venta)
        return cursor.fetchone()[0]

    @staticmethod
    def obtener_o_crear_unidad(cursor, unidad, equivalencia, id_tipo_venta):
        unidad = (unidad or "Sin unidad").strip()
        equivalencia = ClaseDB.sql_valor(equivalencia)
        cursor.execute("""
            SELECT id_unidad
            FROM DIM_UNIDAD
            WHERE unidad = ? AND id_tipo_venta = ?
        """, unidad, id_tipo_venta)
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("""
            INSERT INTO DIM_UNIDAD (unidad, equivalencia, id_tipo_venta)
            OUTPUT INSERTED.id_unidad
            VALUES (?, ?, ?)
        """, unidad, equivalencia, id_tipo_venta)
        return cursor.fetchone()[0]
