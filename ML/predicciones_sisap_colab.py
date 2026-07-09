"""
Predicciones SISAP utilizando Supabase PostgreSQL.

Arquitectura

Supabase
    ↓
Pandas
    ↓
Machine Learning
    ↓
Supabase
"""

import numpy as np
import pandas as pd
import psycopg2
from sqlalchemy import create_engine


# ==========================================================
# CONEXION SUPABASE
# ==========================================================

HOST = "db.xddokslbbzozptctpioe.supabase.co"
DATABASE = "postgres"
USER = "postgres"
PASSWORD = "Guarniz2006@"
PORT = 5432


conn = psycopg2.connect(
    host=HOST,
    database=DATABASE,
    user=USER,
    password=PASSWORD,
    port=PORT,
    sslmode="require"
)

engine = create_engine(
    f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
)


# ==========================================================
# FUNCION DE PROYECCION
# ==========================================================

def proyectar(serie, periodos=8):

    valores = (
        pd.to_numeric(
            serie,
            errors="coerce"
        )
        .dropna()
        .astype(float)
        .tolist()
    )

    if len(valores) == 0:
        return 0.0

    if len(valores) == 1:
        return float(valores[0])

    x = np.arange(len(valores), dtype=float)

    pendiente, intercepto = np.polyfit(
        x,
        valores,
        1
    )

    prediccion = intercepto + pendiente * (
        len(valores) - 1 + periodos
    )

    return max(0.0, float(prediccion))


# ==========================================================
# LEER DATAWAREHOUSE
# ==========================================================

query = """

SELECT *

FROM vw_capa_semantica_bi

ORDER BY fecha

"""

df = pd.read_sql(query, conn)


# ==========================================================
# LIMPIEZA
# ==========================================================

df["fecha"] = pd.to_datetime(df["fecha"])

for columna in [

    "preciominimo",
    "preciopromedio",
    "preciomaximo",
    "variacionprecio"

]:

    df[columna] = pd.to_numeric(
        df[columna],
        errors="coerce"
    )

df = df.dropna(
    subset=[
        "fecha",
        "producto",
        "preciopromedio"
    ]
)


# ==========================================================
# SERIES
# ==========================================================

serie_precio = (

    df

    .groupby("fecha")["preciopromedio"]

    .mean()

    .sort_index()

)

serie_variacion = (

    df

    .groupby("fecha")["variacionprecio"]

    .mean()

    .sort_index()

)

canales = (

    df

    .groupby(
        [
            "fecha",
            "tipoventa"
        ]
    )["preciopromedio"]

    .mean()

    .unstack()

)

serie_diferencia = (

    canales["Minorista"]

    -

    canales["Mayorista"]

).dropna()


# ==========================================================
# RANKING
# ==========================================================

incrementos = []

for producto, grupo in df.groupby("producto"):

    serie = (

        grupo

        .groupby("fecha")["preciopromedio"]

        .mean()

        .sort_index()

    )

    if len(serie):

        incremento = proyectar(serie) - float(serie.iloc[-1])

        incrementos.append(

            {

                "producto": producto,

                "incrementoesperado": incremento

            }

        )

ranking_incrementos = (

    pd.DataFrame(incrementos)

    .sort_values(

        "incrementoesperado",

        ascending=False

    )

)


# ==========================================================
# PREDICCION 8 SEMANAS
# ==========================================================

fechas = pd.date_range(

    start=df["fecha"].max() + pd.Timedelta(days=7),

    periods=8,

    freq="7D"

)

salida = pd.DataFrame(

    {

        "fechaprediccion": fechas,

        "preciopromediofuturo": [

            proyectar(serie_precio, i)

            for i in range(1, 9)

        ],

        "tendenciavariacion": [

            proyectar(serie_variacion, i)

            for i in range(1, 9)

        ],

        "diferenciamayoristaminoristafutura": [

            proyectar(serie_diferencia, i)

            for i in range(1, 9)

        ]

    }

)

if not ranking_incrementos.empty:

    salida["productomayorincremento"] = ranking_incrementos.iloc[0]["producto"]

else:

    salida["productomayorincremento"] = "Sin datos"


# ==========================================================
# GUARDAR EN SUPABASE
# ==========================================================

salida.to_sql(

    "predicciones_sisap",

    engine,

    if_exists="replace",

    index=False

)

ranking_incrementos.to_sql(

    "ranking_incrementos",

    engine,

    if_exists="replace",

    index=False

)


# ==========================================================
# MOSTRAR RESULTADOS
# ==========================================================

print("\nPredicciones\n")

print(salida)

print("\nRanking\n")

print(ranking_incrementos.head(10))


# ==========================================================
# CERRAR CONEXION
# ==========================================================

conn.close()
