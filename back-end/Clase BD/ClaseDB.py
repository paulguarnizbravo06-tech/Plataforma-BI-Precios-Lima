import numpy as np
import pandas as pd
import psycopg2


class ClaseDB:
    """Conexión y operaciones auxiliares para Supabase PostgreSQL."""

@staticmethod
def conectar_db():
    return psycopg2.connect(
        host="aws-1-us-east-2.pooler.supabase.com",
        database="postgres",
        user="postgres.ksuuystvousnqdfxzwrx",
        password="Guarniz2006@",
        port=6543,
        sslmode="require"
    )

    @staticmethod
    def sql_valor(v):
        """Convierte NaN/NaT en NULL."""
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

        cursor.execute(
            """
            SELECT id_producto
            FROM dim_producto
            WHERE producto=%s
            """,
            (producto,)
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        cursor.execute(
            """
            INSERT INTO dim_producto(producto)
            VALUES(%s)
            RETURNING id_producto
            """,
            (producto,)
        )

        return cursor.fetchone()[0]

    @staticmethod
    def obtener_o_crear_tipo_venta(cursor, tipo_venta):

        tipo_venta = (tipo_venta or "No especificado").strip()

        cursor.execute(
            """
            SELECT id_tipo_venta
            FROM dim_tipo_venta
            WHERE tipo_venta=%s
            """,
            (tipo_venta,)
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        cursor.execute(
            """
            INSERT INTO dim_tipo_venta(tipo_venta)
            VALUES(%s)
            RETURNING id_tipo_venta
            """,
            (tipo_venta,)
        )

        return cursor.fetchone()[0]

    @staticmethod
    def obtener_o_crear_unidad(cursor, unidad, equivalencia, id_tipo_venta):

        unidad = (unidad or "Sin unidad").strip()
        equivalencia = ClaseDB.sql_valor(equivalencia)

        cursor.execute(
            """
            SELECT id_unidad
            FROM dim_unidad
            WHERE unidad=%s
            AND id_tipo_venta=%s
            """,
            (unidad, id_tipo_venta)
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        cursor.execute(
            """
            INSERT INTO dim_unidad
            (
                unidad,
                equivalencia,
                id_tipo_venta
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            RETURNING id_unidad
            """,
            (
                unidad,
                equivalencia,
                id_tipo_venta
            )
        )

        return cursor.fetchone()[0]

    @staticmethod
    def guardar(conn):
        conn.commit()

    @staticmethod
    def rollback(conn):
        conn.rollback()

    @staticmethod
    def cerrar(cursor=None, conn=None):

        if cursor:
            cursor.close()

        if conn:
            conn.close()
