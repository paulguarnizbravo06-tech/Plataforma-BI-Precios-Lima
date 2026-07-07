import pandas as pd
import numpy as np

class ClaseML:
    """Clase encargada del análisis, KPIs y reglas predictivas del proyecto BI."""

    @staticmethod
    def ejecutar_etl(staging_data):
        df = pd.DataFrame(staging_data)
        for col in ["precio_mayorista", "precio_minorista", "precio_analisis"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["precio_unitario"] = df[["precio_mayorista", "precio_minorista"]].mean(axis=1)
        df["diferencia_precio"] = df["precio_minorista"] - df["precio_mayorista"]
        rangos = pd.concat([
            pd.to_numeric(df["may_max"], errors="coerce") - pd.to_numeric(df["may_min"], errors="coerce"),
            pd.to_numeric(df["min_max"], errors="coerce") - pd.to_numeric(df["min_min"], errors="coerce")
        ], axis=1)
        df["variacion_precio"] = rangos.mean(axis=1)
        return df.replace([np.inf, -np.inf], np.nan).to_dict(orient="records")

    @staticmethod
    def calcular_kpis(dw_data):
        df = pd.DataFrame(dw_data)
        for col in [
            "precio_mayorista", "precio_minorista", "precio_analisis", "variacion_precio",
            "may_min", "may_max", "min_min", "min_max"
        ]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        promedios = pd.concat([df["precio_mayorista"], df["precio_minorista"]]).dropna()
        minimos = pd.concat([df["may_min"], df["min_min"]]).dropna()
        maximos = pd.concat([df["may_max"], df["min_max"]]).dropna()
        precio_prom = float(promedios.mean()) if not promedios.empty else 0.0
        precio_max = float(maximos.max()) if not maximos.empty else 0.0
        precio_min = float(minimos.min()) if not minimos.empty else 0.0
        var_promedio = float(df["variacion_precio"].dropna().mean()) if df["variacion_precio"].notna().any() else 0.0
        return {
            "precio_promedio_general": round(precio_prom, 2),
            "precio_maximo_registrado": round(precio_max, 2),
            "precio_minimo_registrado": round(precio_min, 2),
            "variacion_promedio": round(var_promedio, 2),
            "total_productos_catalogados": int(df["producto"].nunique())
        }
