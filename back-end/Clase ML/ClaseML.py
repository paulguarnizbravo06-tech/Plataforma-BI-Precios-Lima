import pandas as pd
import numpy as np


class ClaseML:
    """
    Clase encargada del análisis,
    KPIs y reglas de negocio.
    No realiza conexiones a la base de datos.
    Recibe DataFrames provenientes de ClaseDB.
    """

    # ======================================================
    # ETL
    # ======================================================

    @staticmethod
    def ejecutar_etl(df):

        df = df.copy()

        columnas = [
            "preciominimo",
            "preciopromedio",
            "preciomaximo",
            "variacionprecio"
        ]

        for columna in columnas:

            if columna in df.columns:

                df[columna] = pd.to_numeric(
                    df[columna],
                    errors="coerce"
                )

        if "preciopromedio" in df.columns:

            df["precio_unitario"] = df["preciopromedio"]

        if "variacionprecio" in df.columns:

            df["diferencia_precio"] = df["variacionprecio"]

        df = df.replace(
            [np.inf, -np.inf],
            np.nan
        )

        return df

    # ======================================================
    # KPIs
    # ======================================================

    @staticmethod
    def calcular_kpis(df):

        df = df.copy()

        columnas = [
            "preciominimo",
            "preciopromedio",
            "preciomaximo",
            "variacionprecio"
        ]

        for columna in columnas:

            if columna in df.columns:

                df[columna] = pd.to_numeric(
                    df[columna],
                    errors="coerce"
                )

        precio_promedio = float(

            df["preciopromedio"].mean()

        ) if "preciopromedio" in df.columns else 0

        precio_maximo = float(

            df["preciomaximo"].max()

        ) if "preciomaximo" in df.columns else 0

        precio_minimo = float(

            df["preciominimo"].min()

        ) if "preciominimo" in df.columns else 0

        variacion = float(

            df["variacionprecio"].mean()

        ) if "variacionprecio" in df.columns else 0

        total_productos = int(

            df["producto"].nunique()

        ) if "producto" in df.columns else 0

        return {

            "precio_promedio_general":
                round(precio_promedio, 2),

            "precio_maximo_registrado":
                round(precio_maximo, 2),

            "precio_minimo_registrado":
                round(precio_minimo, 2),

            "variacion_promedio":
                round(variacion, 2),

            "total_productos_catalogados":
                total_productos

        }

    # ======================================================
    # Ranking productos
    # ======================================================

    @staticmethod
    def ranking_productos(df):

        if "producto" not in df.columns:
            return pd.DataFrame()

        resultado = (

            df.groupby("producto")["preciopromedio"]
            .mean()
            .reset_index()

        )

        resultado.columns = [

            "Producto",
            "PrecioPromedio"

        ]

        resultado = resultado.sort_values(

            by="PrecioPromedio",
            ascending=False

        )

        resultado["Ranking"] = np.arange(

            1,
            len(resultado) + 1

        )

        return resultado

    # ======================================================
    # Grafico Lineal
    # ======================================================

    @staticmethod
    def grafico_lineas(df):

        resultado = (

            df.groupby("fecha")["preciopromedio"]
            .mean()
            .reset_index()

        )

        resultado.columns = [

            "Fecha",
            "PrecioPromedio"

        ]

        return resultado

    # ======================================================
    # Grafico Circular
    # ======================================================

    @staticmethod
    def grafico_circular(df):

        resultado = (

            df.groupby("tipoventa")["preciopromedio"]
            .mean()
            .reset_index()

        )

        resultado.columns = [

            "TipoVenta",
            "PrecioPromedio"

        ]

        return resultado

    # ======================================================
    # Top 10
    # ======================================================

    @staticmethod
    def top10(df):

        ranking = ClaseML.ranking_productos(df)

        return ranking.head(10)

    # ======================================================
    # Predicción Lineal
    # ======================================================

    @staticmethod
    def predecir(serie, semanas=8):

        serie = pd.to_numeric(

            serie,
            errors="coerce"

        ).dropna()

        if len(serie) == 0:

            return 0

        if len(serie) == 1:

            return float(serie.iloc[0])

        x = np.arange(

            len(serie),
            dtype=float

        )

        pendiente, intercepto = np.polyfit(

            x,
            serie,
            1

        )

        return float(

            intercepto +
            pendiente *
            (len(serie) - 1 + semanas)

        )

    # ======================================================
    # Predicciones futuras
    # ======================================================

    @staticmethod
    def generar_predicciones(df):

        serie = (

            df.groupby("fecha")["preciopromedio"]
            .mean()
            .sort_index()

        )

        ultima_fecha = pd.to_datetime(

            serie.index.max()

        )

        fechas = pd.date_range(

            start=ultima_fecha + pd.Timedelta(days=7),
            periods=8,
            freq="7D"

        )

        precios = []

        for i in range(1, 9):

            precios.append(

                ClaseML.predecir(
                    serie,
                    i
                )

            )

        return pd.DataFrame({

            "FechaPrediccion": fechas,
            "PrecioPromedioFuturo": precios

        })

    # ======================================================
    # Producto con mayor incremento esperado
    # ======================================================

    @staticmethod
    def ranking_incrementos(df):

        resultados = []

        for producto, grupo in df.groupby("producto"):

            serie = (

                grupo
                .sort_values("fecha")
                ["preciopromedio"]

            )

            if len(serie) < 2:
                continue

            futuro = ClaseML.predecir(serie)

            incremento = futuro - serie.iloc[-1]

            resultados.append({

                "Producto": producto,
                "IncrementoEsperado": incremento

            })

        ranking = pd.DataFrame(resultados)

        if ranking.empty:
            return ranking

        ranking = ranking.sort_values(

            "IncrementoEsperado",
            ascending=False

        )

        ranking["Ranking"] = np.arange(

            1,
            len(ranking) + 1

        )

        return ranking
