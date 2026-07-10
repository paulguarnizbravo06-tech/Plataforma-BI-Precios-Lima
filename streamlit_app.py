from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text


st.set_page_config(
    page_title="BI Precios Lima",
    page_icon="BI",
    layout="wide",
)

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def get_database_url() -> str | None:
    try:
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return os.getenv("DATABASE_URL")


@st.cache_resource
def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def preparar_raw(raw: pd.DataFrame, origen: str) -> pd.DataFrame | None:
    if raw.empty:
        return None

    fecha_col = pd.to_datetime(raw.iloc[:, 0], errors="coerce", dayfirst=True)
    idx_validos = fecha_col[fecha_col.notna()].index
    if len(idx_validos) == 0:
        return None

    inicio = int(idx_validos.min())
    df = raw.iloc[inicio:].copy()
    for c in range(df.shape[1], 12):
        df[c] = np.nan
    df = df.iloc[:, :12]
    df.columns = [
        "fecha", "producto", "unidad_may", "equiv_may", "may_min", "may_prom", "may_max",
        "unidad_min", "equiv_min", "min_min", "min_prom", "min_max",
    ]
    df["hoja_origen"] = origen
    return df


def obtener_datos(archivo) -> pd.DataFrame:
    partes: list[pd.DataFrame] = []
    filename = (archivo.name or "").lower()

    if filename.endswith(".csv"):
        try:
            raw = pd.read_csv(archivo, header=None, names=range(12), sep=";", engine="python", encoding="utf-8-sig")
        except Exception:
            archivo.seek(0)
            raw = pd.read_csv(archivo, header=None, names=range(12), sep=None, engine="python", encoding="utf-8-sig")
        df_csv = preparar_raw(raw, "CSV")
        if df_csv is not None:
            partes.append(df_csv)
    else:
        xls = pd.ExcelFile(archivo)
        for hoja in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name=hoja, header=None)
            df_hoja = preparar_raw(raw, hoja)
            if df_hoja is not None:
                partes.append(df_hoja)

    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    df = df.dropna(subset=["fecha", "producto"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["fecha"])
    df["producto"] = df["producto"].astype(str).str.strip()

    for col in ["may_min", "may_prom", "may_max", "min_min", "min_prom", "min_max", "equiv_may", "equiv_min"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["precio_mayorista"] = df["may_prom"]
    df["precio_minorista"] = df["min_prom"]
    df["precio_analisis"] = df["precio_minorista"].combine_first(df["precio_mayorista"])
    df["tipo_precio"] = np.where(df["precio_minorista"].notna(), "Minorista", "Mayorista")
    df["estado"] = "OK"
    df["error"] = ""
    df.loc[df["producto"].str.len() < 3, "error"] += "Nombre producto invalido | "
    df.loc[df["precio_analisis"].isna() | (df["precio_analisis"] <= 0), "error"] += "Sin precio valido | "
    df.loc[df["error"] != "", "estado"] = "ERROR"
    return df


def construir_hechos(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for _, row in df.iterrows():
        fecha = pd.to_datetime(row.get("fecha"), errors="coerce")
        producto = str(row.get("producto") or "").strip()
        if pd.isna(fecha) or not producto:
            continue
        ventas = [
            ("Mayorista", "unidad_may", "equiv_may", "may_min", "precio_mayorista", "may_max"),
            ("Minorista", "unidad_min", "equiv_min", "min_min", "precio_minorista", "min_max"),
        ]
        for tipo, unidad_col, equiv_col, min_col, prom_col, max_col in ventas:
            precio_prom = pd.to_numeric(row.get(prom_col), errors="coerce")
            if pd.isna(precio_prom):
                continue
            precio_min = pd.to_numeric(row.get(min_col), errors="coerce")
            precio_max = pd.to_numeric(row.get(max_col), errors="coerce")
            filas.append({
                "fecha": fecha.date(),
                "producto": producto,
                "tipo_venta": tipo,
                "unidad": str(row.get(unidad_col) or "Sin unidad").strip(),
                "equivalencia": None if pd.isna(row.get(equiv_col)) else float(row.get(equiv_col)),
                "precio_min": None if pd.isna(precio_min) else float(precio_min),
                "precio_prom": float(precio_prom),
                "precio_max": None if pd.isna(precio_max) else float(precio_max),
            })
    hechos = pd.DataFrame(filas)
    if not hechos.empty:
        hechos["variacion_precio"] = hechos["precio_max"] - hechos["precio_min"]
    return hechos


def proyectar(serie: pd.Series, periodos: int = 8) -> float:
    valores = pd.to_numeric(serie, errors="coerce").dropna().astype(float).tolist()
    if not valores:
        return 0.0
    if len(valores) == 1:
        return valores[0]
    x = np.arange(len(valores), dtype=float)
    pendiente, intercepto = np.polyfit(x, valores, 1)
    return max(0.0, float(intercepto + pendiente * (len(valores) - 1 + periodos)))


def ejecutar_sql_schema(engine) -> None:
    with open("BD/script_supabase_postgresql.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    with engine.begin() as conn:
        conn.execute(text(sql))


def obtener_id(conn, tabla: str, id_col: str, campo: str, valor, extra_where: str = "", extra_params: dict | None = None) -> int:
    params = {"valor": valor}
    if extra_params:
        params.update(extra_params)
    row = conn.execute(text(f"select {id_col} from {tabla} where {campo} = :valor {extra_where} limit 1"), params).fetchone()
    if row:
        return int(row[0])
    raise LookupError(f"No existe {tabla}.{campo}={valor}")


def insertar_dimensiones_y_hechos(engine, raw_ok: pd.DataFrame, hechos: pd.DataFrame, reemplazar: bool) -> int:
    with engine.begin() as conn:
        if reemplazar:
            conn.execute(text("delete from fact_kpis"))
            conn.execute(text("delete from fact_precios"))
            conn.execute(text("delete from stg_precios_raw"))

        for _, row in raw_ok.iterrows():
            unidad = row.get("unidad_min") or row.get("unidad_may") or "Sin unidad"
            conn.execute(text("""
                insert into stg_precios_raw
                (fecha_registro, producto_nombre, unidad_medida, precio_mayorista_orig, precio_minorista_orig, hoja_origen)
                values (:fecha, :producto, :unidad, :may, :min, :hoja)
            """), {
                "fecha": pd.to_datetime(row["fecha"]).date(),
                "producto": row.get("producto"),
                "unidad": unidad,
                "may": None if pd.isna(row.get("precio_mayorista")) else float(row.get("precio_mayorista")),
                "min": None if pd.isna(row.get("precio_minorista")) else float(row.get("precio_minorista")),
                "hoja": row.get("hoja_origen"),
            })

        insertados = 0
        for _, row in hechos.iterrows():
            fecha_dt = pd.to_datetime(row["fecha"])
            anio = int(fecha_dt.year)
            mes = int(fecha_dt.month)
            dia = int(fecha_dt.day)

            conn.execute(text("insert into dim_producto(producto) values (:v) on conflict(producto) do nothing"), {"v": row["producto"]})
            conn.execute(text("insert into dim_anio(anio) values (:v) on conflict(anio) do nothing"), {"v": anio})
            id_producto = obtener_id(conn, "dim_producto", "id_producto", "producto", row["producto"])
            id_anio = obtener_id(conn, "dim_anio", "id_anio", "anio", anio)

            conn.execute(text("""
                insert into dim_mes(mes, nombre_mes, id_anio)
                values (:mes, :nombre, :id_anio)
                on conflict(id_anio, mes) do nothing
            """), {"mes": mes, "nombre": MESES[mes - 1], "id_anio": id_anio})
            id_mes = conn.execute(
                text("select id_mes from dim_mes where id_anio = :id_anio and mes = :mes"),
                {"id_anio": id_anio, "mes": mes},
            ).scalar_one()

            conn.execute(text("""
                insert into dim_tiempo(fecha, dia, id_mes)
                values (:fecha, :dia, :id_mes)
                on conflict(fecha) do nothing
            """), {"fecha": fecha_dt.date(), "dia": dia, "id_mes": id_mes})
            id_tiempo = obtener_id(conn, "dim_tiempo", "id_tiempo", "fecha", fecha_dt.date())

            conn.execute(text("insert into dim_tipo_venta(tipo_venta) values (:v) on conflict(tipo_venta) do nothing"), {"v": row["tipo_venta"]})
            id_tipo = obtener_id(conn, "dim_tipo_venta", "id_tipo_venta", "tipo_venta", row["tipo_venta"])

            conn.execute(text("""
                insert into dim_unidad(unidad, equivalencia, id_tipo_venta)
                values (:unidad, :equiv, :id_tipo)
                on conflict(unidad, id_tipo_venta) do nothing
            """), {"unidad": row["unidad"], "equiv": row["equivalencia"], "id_tipo": id_tipo})
            id_unidad = conn.execute(
                text("select id_unidad from dim_unidad where unidad = :unidad and id_tipo_venta = :id_tipo"),
                {"unidad": row["unidad"], "id_tipo": id_tipo},
            ).scalar_one()

            conn.execute(text("""
                insert into fact_precios
                (id_producto, id_tiempo, id_unidad, id_tipo_venta, precio_min, precio_prom, precio_max)
                values (:id_producto, :id_tiempo, :id_unidad, :id_tipo, :pmin, :pprom, :pmax)
            """), {
                "id_producto": id_producto,
                "id_tiempo": id_tiempo,
                "id_unidad": id_unidad,
                "id_tipo": id_tipo,
                "pmin": row["precio_min"],
                "pprom": row["precio_prom"],
                "pmax": row["precio_max"],
            })
            insertados += 1

        kpis = hechos.agg({
            "precio_prom": "mean",
            "precio_max": "max",
            "precio_min": "min",
            "variacion_precio": "mean",
        })
        metas = {
            "Precio Promedio General": (kpis["precio_prom"], "Mantener estabilidad de precios"),
            "Precio Maximo Registrado": (kpis["precio_max"], "Identificar precios elevados"),
            "Precio Minimo Registrado": (kpis["precio_min"], "Identificar precios bajos"),
            "Variacion Promedio": (kpis["variacion_precio"], "Monitorear rango maximo - minimo"),
        }
        for nombre, (valor, meta) in metas.items():
            conn.execute(text("insert into fact_kpis(nombre_kpi, valor, meta) values (:n, :v, :m)"), {
                "n": nombre,
                "v": None if pd.isna(valor) else float(valor),
                "m": meta,
            })
    return insertados


def cargar_capa_semantica(engine) -> pd.DataFrame:
    try:
        return pd.read_sql("select * from vw_capa_semantica_bi", engine)
    except Exception:
        return pd.DataFrame()


st.title("Plataforma BI Precios Lima")
st.caption("GitHub + Supabase PostgreSQL + Streamlit Community Cloud")
pasos_flujo = [
    ("Paso 1", "Fuentes de Datos", "Captura de archivos SISAP"),
    ("Paso 2", "Staging Area", "Validacion y control de calidad"),
    ("Paso 3", "Proceso ETL", "Transformacion de datos"),
    ("Paso 4", "Data Warehouse", "Carga en Supabase PostgreSQL"),
    ("Paso 5", "Capa de IA", "Predicciones de precios"),
    ("Paso 6", "Capa Semantica & KPIs", "Indicadores ejecutivos"),
    ("Paso 7", "Visualizacion BI", "Dashboard final"),
]

cols = st.columns(4)
for idx, (paso, titulo, detalle) in enumerate(pasos_flujo):
    with cols[idx % 4]:
        st.markdown(
            f"""
            <div style="border:1px solid #d8dee9;border-radius:8px;padding:14px 16px;margin-bottom:12px;min-height:112px;background:#ffffff;">
                <div style="font-size:12px;font-weight:700;color:#2563eb;">{paso}</div>
                <div style="font-size:16px;font-weight:700;margin-top:8px;color:#111827;">{titulo}</div>
                <div style="font-size:13px;margin-top:6px;color:#6b7280;">{detalle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

database_url = get_database_url()
if not database_url:
    st.warning("Configura DATABASE_URL en Streamlit Secrets para conectar con Supabase.")
    st.stop()

engine = get_engine(database_url)

with st.sidebar:
    st.header("Flujo BI")
    st.caption("7 pasos del flujo BI")
    pagina = st.radio(
        "Modulo",
        [
            "1. Fuentes de Datos",
            "2. Staging Area",
            "3. Proceso ETL",
            "4. Data Warehouse",
            "5. Capa de IA",
            "6. Capa Semantica & KPIs",
            "7. Visualizacion BI",
        ],
    )
    if st.button("Crear/actualizar tablas Supabase"):
        try:
            ejecutar_sql_schema(engine)
            st.success("Tablas y vistas verificadas en Supabase.")
        except Exception as exc:
            st.error(f"No se pudo ejecutar el schema: {exc}")

if "raw_df" not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if "ok_df" not in st.session_state:
    st.session_state.ok_df = pd.DataFrame()
if "hechos_df" not in st.session_state:
    st.session_state.hechos_df = pd.DataFrame()

if pagina == "1. Fuentes de Datos":
    st.subheader("Fuentes de datos")
    archivo = st.file_uploader("Carga archivo SISAP en Excel o CSV", type=["xlsx", "xls", "csv"])
    if archivo:
        df = obtener_datos(archivo)
        st.session_state.raw_df = df
        st.session_state.ok_df = df[df["estado"] == "OK"].copy()
        st.success(f"Registros leidos: {len(df)} | Validos: {len(st.session_state.ok_df)}")
        st.dataframe(df.head(100), use_container_width=True)

elif pagina == "2. Staging Area":
    st.subheader("Staging Area")
    raw_df = st.session_state.raw_df
    ok_df = st.session_state.ok_df
    if raw_df.empty:
        st.info("Primero carga un archivo en Fuentes de Datos.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Registros fuente", len(raw_df))
        col2.metric("Registros OK", len(ok_df))
        col3.metric("Errores", int((raw_df["estado"] == "ERROR").sum()))
        st.dataframe(raw_df.head(100), use_container_width=True)

elif pagina == "3. Proceso ETL":
    st.subheader("Proceso ETL")
    ok_df = st.session_state.ok_df
    if ok_df.empty:
        st.info("Primero valida registros en Staging Area.")
    else:
        hechos = construir_hechos(ok_df)
        st.session_state.hechos_df = hechos
        col1, col2, col3 = st.columns(3)
        col1.metric("Registros limpios", len(ok_df))
        col2.metric("Hechos generados", len(hechos))
        col3.metric("Productos", int(hechos["producto"].nunique()) if not hechos.empty else 0)
        st.dataframe(hechos.head(100), use_container_width=True)
        st.success("ETL preparado. Continua al paso 4 para cargar el Data Warehouse.")

elif pagina == "4. Data Warehouse":
    st.subheader("Data Warehouse en Supabase")
    ok_df = st.session_state.ok_df
    hechos = st.session_state.hechos_df
    if ok_df.empty or hechos.empty:
        st.info("Primero ejecuta Fuentes, Staging y Proceso ETL.")
    else:
        reemplazar = st.checkbox("Reemplazar hechos anteriores en Supabase", value=True)
        if st.button("Guardar Data Warehouse en Supabase"):
            try:
                ejecutar_sql_schema(engine)
                insertados = insertar_dimensiones_y_hechos(engine, ok_df, hechos, reemplazar)
                st.success(f"Data Warehouse cargado en Supabase. Hechos insertados: {insertados}")
            except Exception as exc:
                st.error(f"Error al guardar en Supabase: {exc}")

    df = cargar_capa_semantica(engine)
    if df.empty:
        st.info("Aun no hay datos en la vista vw_capa_semantica_bi.")
    else:
        st.metric("Filas analiticas", len(df))
        st.dataframe(df.head(200), use_container_width=True)

elif pagina == "5. Capa de IA":
    st.subheader("Capa de IA")
    df = cargar_capa_semantica(engine)
    if df.empty:
        st.info("Carga datos al Data Warehouse primero.")
    else:
        df["fecha"] = pd.to_datetime(df["fecha"])
        predicciones = []
        for producto, grupo in df.groupby("producto"):
            serie = grupo.groupby("fecha")["precio_promedio"].mean().sort_index()
            if not serie.empty:
                actual = float(serie.iloc[-1])
                futuro = proyectar(serie, periodos=8)
                predicciones.append({
                    "Producto": producto,
                    "Precio actual": round(actual, 2),
                    "Precio predicho 8 semanas": round(futuro, 2),
                    "Incremento esperado": round(futuro - actual, 2),
                })
        pred = pd.DataFrame(predicciones).sort_values("Incremento esperado", ascending=False)
        st.dataframe(pred, use_container_width=True)

elif pagina == "6. Capa Semantica & KPIs":
    st.subheader("Capa Semantica & KPIs")
    df = cargar_capa_semantica(engine)
    if df.empty:
        st.info("Carga datos al Data Warehouse primero.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Precio promedio", f"{df['precio_promedio'].mean():.2f}")
        c2.metric("Precio maximo", f"{df['precio_maximo'].max():.2f}")
        c3.metric("Precio minimo", f"{df['precio_minimo'].min():.2f}")
        c4.metric("Variacion promedio", f"{df['variacion_precio'].mean():.2f}")
        c5.metric("Productos", int(df["producto"].nunique()))
        st.dataframe(df.head(200), use_container_width=True)

elif pagina == "7. Visualizacion BI":
    st.subheader("Visualizacion BI")
    df = cargar_capa_semantica(engine)
    if df.empty:
        st.info("No hay datos para graficar.")
    else:
        df["fecha"] = pd.to_datetime(df["fecha"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio promedio", f"{df['precio_promedio'].mean():.2f}")
        c2.metric("Precio maximo", f"{df['precio_maximo'].max():.2f}")
        c3.metric("Precio minimo", f"{df['precio_minimo'].min():.2f}")
        c4.metric("Productos", int(df["producto"].nunique()))

        top = df.groupby("producto", as_index=False)["precio_promedio"].mean().sort_values("precio_promedio", ascending=False).head(10)
        evolucion = df.groupby("fecha", as_index=False)["precio_promedio"].mean().sort_values("fecha")
        canales = df.groupby("tipo_venta", as_index=False)["precio_promedio"].mean()

        st.plotly_chart(px.bar(top, x="producto", y="precio_promedio", title="Top 10 productos por precio promedio"), use_container_width=True)
        st.plotly_chart(px.line(evolucion, x="fecha", y="precio_promedio", markers=True, title="Evolucion del precio promedio"), use_container_width=True)
        st.plotly_chart(px.pie(canales, names="tipo_venta", values="precio_promedio", title="Precio promedio por canal"), use_container_width=True)




