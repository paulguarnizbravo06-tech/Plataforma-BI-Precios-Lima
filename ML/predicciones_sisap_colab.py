"""Predicciones SISAP a 8 semanas para ejecutar en Google Colab."""

import pandas as pd
import numpy as np


def proyectar(serie, periodos=8):
    valores = pd.to_numeric(serie, errors="coerce").dropna().astype(float).tolist()
    if not valores:
        return 0.0
    if len(valores) == 1:
        return valores[0]
    x = np.arange(len(valores), dtype=float)
    pendiente, intercepto = np.polyfit(x, valores, 1)
    return max(0.0, float(intercepto + pendiente * (len(valores) - 1 + periodos)))


raw = pd.read_csv("/content/precios_sisap.csv", sep=";", encoding="utf-8-sig", skiprows=4)
raw.columns = [
    "fecha", "producto", "unidad_mayorista", "equiv_mayorista",
    "precio_min_mayorista", "precio_prom_mayorista", "precio_max_mayorista",
    "unidad_minorista", "equiv_minorista", "precio_min_minorista",
    "precio_prom_minorista", "precio_max_minorista"
]
raw["fecha"] = pd.to_datetime(raw["fecha"], dayfirst=True, errors="coerce")

may = raw[[
    "fecha", "producto", "unidad_mayorista", "equiv_mayorista",
    "precio_min_mayorista", "precio_prom_mayorista", "precio_max_mayorista"
]].copy()
may.columns = ["fecha", "producto", "unidad", "equivalencia", "precio_min", "precio_prom", "precio_max"]
may["tipo_venta"] = "Mayorista"

minor = raw[[
    "fecha", "producto", "unidad_minorista", "equiv_minorista",
    "precio_min_minorista", "precio_prom_minorista", "precio_max_minorista"
]].copy()
minor.columns = ["fecha", "producto", "unidad", "equivalencia", "precio_min", "precio_prom", "precio_max"]
minor["tipo_venta"] = "Minorista"

df = pd.concat([may, minor], ignore_index=True)
for columna in ["equivalencia", "precio_min", "precio_prom", "precio_max"]:
    df[columna] = pd.to_numeric(df[columna], errors="coerce")
df = df.dropna(subset=["fecha", "producto", "precio_prom"])
df["variacion_precio"] = df["precio_max"] - df["precio_min"]

serie_precio = df.groupby("fecha")["precio_prom"].mean().sort_index()
serie_variacion = df.groupby("fecha")["variacion_precio"].mean().sort_index()
canales = df.groupby(["fecha", "tipo_venta"])["precio_prom"].mean().unstack()
serie_diferencia = (canales["Minorista"] - canales["Mayorista"]).dropna()

incrementos = []
for producto, grupo in df.groupby("producto"):
    serie = grupo.groupby("fecha")["precio_prom"].mean().sort_index()
    if not serie.empty:
        incremento = proyectar(serie) - float(serie.iloc[-1])
        incrementos.append({"Producto": producto, "IncrementoEsperado": incremento})
ranking_incrementos = pd.DataFrame(incrementos).sort_values("IncrementoEsperado", ascending=False)

fechas = pd.date_range(start=df["fecha"].max() + pd.Timedelta(days=7), periods=8, freq="7D")
salida = pd.DataFrame({
    "FechaPrediccion": fechas,
    "PrecioPromedioFuturo": [proyectar(serie_precio, i) for i in range(1, 9)],
    "TendenciaVariacion": [proyectar(serie_variacion, i) for i in range(1, 9)],
    "DiferenciaMayoristaMinoristaFutura": [proyectar(serie_diferencia, i) for i in range(1, 9)]
})
salida["ProductoMayorIncremento"] = ranking_incrementos.iloc[0]["Producto"] if not ranking_incrementos.empty else "Sin datos"

salida.to_csv("/content/predicciones_sisap.csv", index=False)
ranking_incrementos.to_csv("/content/ranking_incrementos_sisap.csv", index=False)
print(salida)
