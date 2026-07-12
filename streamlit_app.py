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

PASOS_FLUJO = [
    ("Paso 1", "Fuentes de Datos", "Captura de archivos SISAP", "Registros crudos", "#38bdf8"),
    ("Paso 2", "Staging Area", "Validacion y control de calidad", "Errores aislados", "#a78bfa"),
    ("Paso 3", "Proceso ETL", "Limpieza y transformacion", "Transformacion base", "#34d399"),
    ("Paso 4", "Data Warehouse", "Carga en Supabase PostgreSQL", "Modelo analitico", "#f59e0b"),
    ("Paso 5", "Capa de IA", "Predicciones de precios", "Modelo lineal", "#818cf8"),
    ("Paso 6", "Capa Semantica & KPIs", "Indicadores ejecutivos", "Medidas de negocio", "#facc15"),
    ("Paso 7", "Visualizacion BI", "Dashboard final", "Panel ejecutivo", "#f472b6"),
]


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
            /* Base Theme Configuration */
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
            
            * {
                font-family: 'Outfit', sans-serif;
            }
            
            .stApp {
                background: #f1f5f9;
                color: #1e293b;
            }
            
            /* Sidebar Custom Styling */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a, #1e3a8a 85%);
                border-right: 2px solid #3b82f6;
            }
            [data-testid="stSidebar"] * {
                color: #f1f5f9 !important;
            }
            /* Hide the radio input circle completely */
            [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
                display: none !important;
            }
            /* Style the wrapper label to look like a button menu item */
            [data-testid="stSidebar"] div[role="radiogroup"] label {
                display: block !important;
                background-color: transparent !important;
                color: #cbd5e1 !important;
                padding: 10px 16px !important;
                font-size: 15px !important;
                font-weight: 500 !important;
                border-radius: 6px !important;
                margin-bottom: 4px !important;
                border: 1px solid transparent !important;
                cursor: pointer !important;
                width: 100% !important;
                transition: background 0.2s, color 0.2s !important;
                box-sizing: border-box !important;
            }
            [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background-color: rgba(59, 130, 246, 0.15) !important;
                color: #ffffff !important;
            }
            /* Active option (checked) */
            [data-testid="stSidebar"] div[role="radiogroup"] [data-checked="true"] label {
                background-color: rgba(59, 130, 246, 0.25) !important;
                color: #38bdf8 !important;
                border-left: 4px solid #38bdf8 !important;
                padding-left: 12px !important;
            }
            /* Add the category title before the second option */
            [data-testid="stSidebar"] div[role="radiogroup"] > div:nth-child(2)::before {
                content: "7 PASOS DEL FLUJO BI";
                display: block;
                font-size: 11px;
                font-weight: 700;
                color: #94a3b8;
                text-transform: uppercase;
                margin-top: 18px;
                margin-bottom: 12px;
                letter-spacing: 0.05em;
                padding-left: 5px;
            }
            
            /* Header and Titles */
            h1, h2, h3, h4, h5, h6 {
                color: #0f172a !important;
                font-weight: 700 !important;
            }
            
            [data-testid="stHeader"] {
                background: rgba(241, 245, 249, 0.95);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid #e2e8f0;
            }
            
            .block-container {
                padding-top: 1.5rem !important;
                max-width: 1600px !important;
            }
            
            /* Header Banner (Premium Topbar) */
            .bi-topbar {
                border-radius: 12px;
                background: linear-gradient(90deg, #091a36 0%, #1e3a8a 100%);
                padding: 24px 30px;
                margin-bottom: 25px;
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
                border: 1px solid #1e40af;
                position: relative;
                overflow: hidden;
            }
            .bi-topbar::after {
                content: '';
                position: absolute;
                top: 0; right: 0; bottom: 0; left: 0;
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, transparent 100%);
                pointer-events: none;
            }
            .bi-topbar h1 {
                color: #ffffff !important;
                font-size: 30px !important;
                line-height: 1.1;
                margin: 0;
                font-weight: 800 !important;
                letter-spacing: .03em;
                text-transform: uppercase;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .bi-topbar p {
                color: #93c5fd !important;
                font-size: 14px;
                margin: 8px 0 0;
                font-weight: 400;
            }
            .bi-cloud-pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                border: 1px solid #1d4ed8;
                background: rgba(30, 58, 138, 0.4);
                color: #dbeafe !important;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 14px;
                margin-top: 15px;
                border-radius: 9999px;
            }
            .bi-dot {
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: #10b981;
                display: inline-block;
                box-shadow: 0 0 8px #10b981;
            }
            
            /* Flow steps banner */
            .bi-step-card {
                border: 1px solid #e2e8f0;
                background: #ffffff;
                border-radius: 10px;
                padding: 18px;
                margin-bottom: 20px;
                min-height: 140px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .bi-step-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            }
            .bi-step-top {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                margin-bottom: 12px;
            }
            .bi-step-badge {
                display: inline-block;
                font-size: 11px;
                font-weight: 800;
                padding: 3px 10px;
                border: 1px solid currentColor;
                background: #f8fafc;
                border-radius: 4px;
            }
            .bi-step-kicker {
                color: #64748b !important;
                font-size: 11px;
                font-weight: 700;
                text-align: right;
                text-transform: uppercase;
            }
            .bi-step-title {
                color: #1e293b !important;
                font-size: 15px;
                font-weight: 800;
                margin-bottom: 5px;
            }
            .bi-step-detail {
                color: #64748b !important;
                font-size: 12px;
                min-height: 32px;
                line-height: 1.3;
            }
            .bi-step-foot {
                border-top: 1px solid #f1f5f9;
                color: #94a3b8 !important;
                font-size: 11px;
                margin-top: 13px;
                padding-top: 8px;
            }
            
            /* KPI Card Premium Styles */
            .kpi-container {
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                background-color: #ffffff;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                border: 1px solid #e2e8f0;
                margin-bottom: 15px;
                transition: transform 0.2s;
            }
            .kpi-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            }
            .kpi-title {
                font-size: 13px;
                font-weight: 700;
                color: #64748b;
                text-transform: uppercase;
                margin-bottom: 6px;
            }
            .kpi-val {
                font-size: 32px;
                font-weight: 800;
                color: #0f172a;
                margin: 0;
            }
            .kpi-meta {
                font-size: 11px;
                color: #94a3b8;
                margin-top: 8px;
                border-top: 1px solid #f1f5f9;
                padding-top: 6px;
            }
            
            /* Dataframes and charts container */
            .stDataFrame, div[data-testid="stPlotlyChart"] {
                border: 1px solid #e2e8f0;
                background-color: #ffffff;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def obtener_datos_analisis(engine) -> pd.DataFrame:
    df = pd.DataFrame()
    # 1. Intentar cargar desde Supabase
    try:
        df = pd.read_sql("select * from vw_capa_semantica_bi", engine)
    except Exception:
        pass
    
    if df.empty:
        try:
            df = pd.read_sql("select * from fact_precios", engine)
        except Exception:
            pass

    # 2. Si no hay conexión o datos en Supabase, usar el fallback local de st.session_state
    if df.empty:
        if "hechos_df" in st.session_state and not st.session_state.hechos_df.empty:
            df = st.session_state.hechos_df.copy()
            # Mapear nombres de columnas locales a los de la vista de base de datos
            col_mapping = {
                "precio_min": "precio_minimo",
                "precio_prom": "precio_promedio",
                "precio_max": "precio_maximo",
                "tipo_venta": "tipo_venta"
            }
            df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

    if df.empty:
        return pd.DataFrame()

    # Estandarizar nombres de columnas (manejar minúsculas/mayúsculas/guiones de Supabase)
    rename_dict = {}
    for col in df.columns:
        col_lower = col.lower().replace("_", "")
        if col_lower == "idprecio":
            rename_dict[col] = "id_precio"
        elif col_lower == "tipoventa":
            rename_dict[col] = "tipo_venta"
        elif col_lower == "preciominimo":
            rename_dict[col] = "precio_minimo"
        elif col_lower == "preciopromedio":
            rename_dict[col] = "precio_promedio"
        elif col_lower == "preciomaximo":
            rename_dict[col] = "precio_maximo"
        elif col_lower == "variacionprecio":
            rename_dict[col] = "variacion_precio"
        elif col_lower == "nombremes":
            rename_dict[col] = "nombre_mes"
    df = df.rename(columns=rename_dict)

    # Conversión de tipos y columnas calculadas temporales
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    df["nombre_mes"] = df["mes"].map(meses_es)
    df["anio"] = df["fecha"].dt.year
    
    if "variacion_precio" not in df.columns and "precio_maximo" in df.columns and "precio_minimo" in df.columns:
        df["variacion_precio"] = df["precio_maximo"] - df["precio_minimo"]
    
    return df


def embellecer_grafico(fig, titulo, tipo="bar"):
    fig.update_layout(
        title={
            'text': f"<b>{titulo}</b>",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 14, 'color': '#0f172a'}
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", size=10, color="#475569"),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    if tipo == "bar":
        fig.update_traces(marker_color='#3b82f6', marker_line_color='#1d4ed8', marker_line_width=1, opacity=0.85)
        fig.update_xaxes(showgrid=False, title_text="")
        fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0", title_text="")
    elif tipo == "line":
        fig.update_traces(line=dict(color='#3b82f6', width=3), marker=dict(size=6, color='#1d4ed8'))
        fig.update_xaxes(showgrid=False, title_text="")
        fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0", title_text="")
    elif tipo == "pie":
        fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(colors=['#3b82f6', '#10b981']))
    return fig


aplicar_estilos()


database_url = get_database_url()
if not database_url:
    st.warning("Configura DATABASE_URL en Streamlit Secrets para conectar con Supabase.")
    st.stop()

engine = get_engine(database_url)

# Cargar vista de base de datos o fallback local
df_analisis = obtener_datos_analisis(engine)
df_filtrado = pd.DataFrame()

with st.sidebar:
    if os.path.exists("front-end/img/logo.png"):
        st.image("front-end/img/logo.png", use_container_width=True)
    st.markdown("### Flujo BI")
    st.caption("7 pasos del flujo BI")
    pagina = st.radio(
        "Modulo",
        [
            "⊞ Pantalla General",
            "① Fuentes de Datos",
            "② Staging Area",
            "③ Proceso ETL",
            "④ Data Warehouse",
            "⑤ Capa de IA",
            "⑥ Capa Semántica & KPIs",
            "⑦ Visualización BI",
        ],
        label_visibility="collapsed"
    )

    # Inyectar filtros de la barra lateral si hay datos y estamos en módulos de visualización/IA
    if not df_analisis.empty and pagina in ["⑤ Capa de IA", "⑥ Capa Semántica & KPIs", "⑦ Visualización BI"]:
        st.markdown("---")
        st.markdown("### 🎯 Zona de Filtros")
        
        # 1. Rango de Fechas
        min_date = df_analisis["fecha"].min().date()
        max_date = df_analisis["fecha"].max().date()
        
        date_val = st.date_input(
            "Rango de Fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_range_picker"
        )
        
        if isinstance(date_val, (list, tuple)) and len(date_val) == 2:
            start_date, end_date = date_val
        else:
            start_date = end_date = date_val[0] if isinstance(date_val, (list, tuple)) and len(date_val) > 0 else min_date
            
        # 2. Selección de Producto
        productos_disponibles = sorted(df_analisis["producto"].dropna().unique().tolist())
        select_all_prod = st.checkbox("Seleccionar todo", value=True, key="sel_all_prod")
        
        productos_seleccionados = []
        if select_all_prod:
            productos_seleccionados = productos_disponibles
        else:
            # Contenedor scrollable nativo de Streamlit
            with st.container(height=200):
                for prod in productos_disponibles:
                    if st.checkbox(prod, value=False, key=f"chk_prod_{prod}"):
                        productos_seleccionados.append(prod)
            if not productos_seleccionados:
                productos_seleccionados = productos_disponibles
        
        # 3. Tipo de Mercado
        st.markdown("**Tipo de Mercado**")
        tipos_venta_disponibles = sorted(df_analisis["tipo_venta"].dropna().unique().tolist())
        tipo_venta_selected = []
        for tv in tipos_venta_disponibles:
            if st.checkbox(tv, value=True, key=f"chk_tv_{tv}"):
                tipo_venta_selected.append(tv)
        if not tipo_venta_selected:
            tipo_venta_selected = tipos_venta_disponibles
            
        # Aplicar filtrado
        df_filtrado = df_analisis[
            (df_analisis["fecha"].dt.date >= start_date) &
            (df_analisis["fecha"].dt.date <= end_date) &
            (df_analisis["producto"].isin(productos_seleccionados)) &
            (df_analisis["tipo_venta"].isin(tipo_venta_selected))
        ]
    else:
        df_filtrado = df_analisis

if "raw_df" not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if "ok_df" not in st.session_state:
    st.session_state.ok_df = pd.DataFrame()
if "hechos_df" not in st.session_state:
    st.session_state.hechos_df = pd.DataFrame()

if pagina == "⊞ Pantalla General":
    st.markdown(
        """
        <div class="bi-topbar">
            <h1>Plataforma BI Integrada - Monitoreo de Precios en Mercados de Lima</h1>
            <p>Arquitectura cloud end-to-end: captura, staging, ETL, warehouse, analitica predictiva y visualizacion ejecutiva.</p>
            <div class="bi-cloud-pill"><span class="bi-dot"></span> GitHub + Supabase PostgreSQL + Streamlit Community Cloud</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    for idx, (paso, titulo, detalle, estado, color) in enumerate(PASOS_FLUJO):
        with cols[idx % 4]:
            st.markdown(
                f"""
                <div class="bi-step-card">
                    <div class="bi-step-top">
                        <span class="bi-step-badge" style="color:{color};">{paso}</span>
                        <span class="bi-step-kicker">{titulo}</span>
                    </div>
                    <div class="bi-step-title">{titulo}</div>
                    <div class="bi-step-detail">{detalle}</div>
                    <div class="bi-step-foot"><span style="color:{color};font-weight:800;">{estado}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

elif pagina == "① Fuentes de Datos":
    st.subheader("Fuentes de datos")
    archivo = st.file_uploader("Carga archivo SISAP en Excel o CSV", type=["xlsx", "xls", "csv"])
    if archivo:
        df = obtener_datos(archivo)
        st.session_state.raw_df = df
        st.session_state.ok_df = df[df["estado"] == "OK"].copy()
        st.success(f"Registros leidos: {len(df)} | Validos: {len(st.session_state.ok_df)}")
        st.dataframe(df.head(100), use_container_width=True)

elif pagina == "② Staging Area":
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

elif pagina == "③ Proceso ETL":
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

elif pagina == "④ Data Warehouse":
    st.subheader("Data Warehouse en Supabase")
    
    # Inicialización local/remota de tablas Supabase (trasladada del sidebar)
    if st.button("Crear / Actualizar estructura de tablas en Supabase"):
        try:
            ejecutar_sql_schema(engine)
            st.success("Tablas y vistas verificadas en Supabase.")
        except Exception as exc:
            st.error(f"Error al inicializar las tablas: {exc}")
            
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

    df = df_analisis
    if df.empty:
        st.info("Aun no hay datos en la vista vw_capa_semantica_bi.")
    else:
        st.metric("Filas analiticas", len(df))
        st.dataframe(df.head(200), use_container_width=True)

elif pagina == "⑤ Capa de IA":
    st.subheader("💡 Capa de Inteligencia Artificial (Predicciones a 8 Semanas)")
    if df_filtrado.empty:
        st.warning("No hay datos suficientes para calcular las predicciones con los filtros activos.")
    else:
        # Preparamos las series temporales
        df_filtrado["fecha"] = pd.to_datetime(df_filtrado["fecha"])
        
        # 1. Serie Precio Promedio General
        serie_precio = df_filtrado.groupby("fecha")["precio_promedio"].mean().sort_index()
        fechas_futuras = pd.date_range(start=serie_precio.index.max() + pd.Timedelta(days=7), periods=8, freq="7D")
        
        precio_futuro = [proyectar(serie_precio, i) for i in range(1, 9)]
        df_precio_hist = pd.DataFrame({"Fecha": serie_precio.index, "Valor": serie_precio.values, "Tipo": "Histórico"})
        df_precio_pred = pd.DataFrame({"Fecha": fechas_futuras, "Valor": precio_futuro, "Tipo": "Proyectado"})
        df_precio_plot = pd.concat([df_precio_hist, df_precio_pred], ignore_index=True)
        fig_precio = px.line(df_precio_plot, x="Fecha", y="Valor", color="Tipo", line_dash="Tipo", labels={"Valor": "Precio Promedio (S/)"})
        fig_precio = embellecer_grafico(fig_precio, "Predicción 1: Precio Promedio Futuro", "line")
        
        # 2. Serie Tendencia de Variación
        serie_var = df_filtrado.groupby("fecha")["variacion_precio"].mean().sort_index()
        var_futuro = [proyectar(serie_var, i) for i in range(1, 9)]
        df_var_hist = pd.DataFrame({"Fecha": serie_var.index, "Valor": serie_var.values, "Tipo": "Histórico"})
        df_var_pred = pd.DataFrame({"Fecha": fechas_futuras, "Valor": var_futuro, "Tipo": "Proyectado"})
        df_var_plot = pd.concat([df_var_hist, df_var_pred], ignore_index=True)
        fig_var = px.line(df_var_plot, x="Fecha", y="Valor", color="Tipo", line_dash="Tipo", labels={"Valor": "Variación Promedio (S/)"})
        fig_var = embellecer_grafico(fig_var, "Predicción 2: Tendencia de Variación de Precios", "line")
        
        # 3. Producto con Mayor Incremento Esperado
        incrementos = []
        for prod, grupo in df_filtrado.groupby("producto"):
            serie_p = grupo.groupby("fecha")["precio_promedio"].mean().sort_index()
            if len(serie_p) >= 1:
                actual = float(serie_p.iloc[-1])
                futuro = proyectar(serie_p, 8)
                inc = futuro - actual
                incrementos.append({
                    "Producto": prod,
                    "Precio actual (S/)": actual,
                    "Precio predicho (S/)": futuro,
                    "Incremento esperado (S/)": inc,
                    "serie": serie_p
                })
        
        df_incrementos = pd.DataFrame(incrementos)
        if not df_incrementos.empty:
            df_incrementos = df_incrementos.sort_values("Incremento esperado (S/)", ascending=False)
            top_inc = df_incrementos.iloc[0]
            prod_name = top_inc["Producto"]
            inc_val = top_inc["Incremento esperado (S/)"]
            serie_p_top = top_inc["serie"]
            
            fechas_futuras_p = pd.date_range(start=serie_p_top.index.max() + pd.Timedelta(days=7), periods=8, freq="7D")
            p_futuro = [proyectar(serie_p_top, i) for i in range(1, 9)]
            df_p_hist = pd.DataFrame({"Fecha": serie_p_top.index, "Precio": serie_p_top.values, "Tipo": "Histórico"})
            df_p_pred = pd.DataFrame({"Fecha": fechas_futuras_p, "Precio": p_futuro, "Tipo": "Proyectado"})
            df_p_plot = pd.concat([df_p_hist, df_p_pred], ignore_index=True)
            
            fig_prod = px.line(df_p_plot, x="Fecha", y="Precio", color="Tipo", line_dash="Tipo", labels={"Precio": "Precio (S/)"})
            fig_prod = embellecer_grafico(fig_prod, f"Predicción 3: {prod_name} (Mayor Incremento Esperado)", "line")
            
            st.info(f"💡 El producto con **mayor incremento esperado** en las próximas 8 semanas es **{prod_name}** con un alza proyectada de **S/ {inc_val:.2f}**.")
        else:
            prod_name = "Sin datos"
            inc_val = 0.0
            fig_prod = px.line()
            fig_prod = embellecer_grafico(fig_prod, "Predicción 3: Producto con Mayor Incremento Esperado", "line")
            
        # 4. Diferencia Mayorista vs Minorista Futura
        por_canal = df_filtrado.groupby(["fecha", "tipo_venta"])["precio_promedio"].mean().unstack()
        if "Minorista" in por_canal.columns and "Mayorista" in por_canal.columns:
            serie_diff = (por_canal["Minorista"] - por_canal["Mayorista"]).dropna().sort_index()
            diff_futuro = [proyectar(serie_diff, i) for i in range(1, 9)]
            df_diff_hist = pd.DataFrame({"Fecha": serie_diff.index, "Brecha": serie_diff.values, "Tipo": "Histórico"})
            df_diff_pred = pd.DataFrame({"Fecha": fechas_futuras, "Brecha": diff_futuro, "Tipo": "Proyectado"})
            df_diff_plot = pd.concat([df_diff_hist, df_diff_pred], ignore_index=True)
            fig_diff = px.line(df_diff_plot, x="Fecha", y="Brecha", color="Tipo", line_dash="Tipo", labels={"Brecha": "Diferencia (S/)"})
            fig_diff = embellecer_grafico(fig_diff, "Predicción 4: Diferencia Mayorista vs Minorista Futura", "line")
        else:
            fig_diff = px.line()
            fig_diff = embellecer_grafico(fig_diff, "Predicción 4: Diferencia Mayorista vs Minorista Futura (Sin datos de ambos canales)", "line")
            
        # Render en Cuadrícula
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig_precio, use_container_width=True)
        with c2:
            st.plotly_chart(fig_var, use_container_width=True)
            
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(fig_prod, use_container_width=True)
        with c4:
            st.plotly_chart(fig_diff, use_container_width=True)
            
        # Tabla resumen de incrementos esperados
        if not df_incrementos.empty:
            st.markdown("### 📊 Tabla de Predicciones por Producto")
            tabla_resumen = df_incrementos.drop(columns=["serie"])
            for c in ["Precio actual (S/)", "Precio predicho (S/)", "Incremento esperado (S/)"]:
                tabla_resumen[c] = tabla_resumen[c].map(lambda x: f"S/ {x:.2f}")
            st.dataframe(tabla_resumen, use_container_width=True, hide_index=True)

elif pagina == "⑥ Capa Semántica & KPIs":
    st.subheader("Capa Semántica & KPIs")
    if df_filtrado.empty:
        st.info("Carga datos al Data Warehouse primero o revisa la selección de tus filtros.")
    else:
        avg_precio = df_filtrado["precio_promedio"].mean()
        max_precio = df_filtrado["precio_maximo"].max()
        min_precio = df_filtrado["precio_minimo"].min()
        var_promedio = df_filtrado["variacion_precio"].mean()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio Promedio General", f"S/ {avg_precio:.2f}", help="Meta: Mantener estabilidad de precios")
        c2.metric("Precio Máximo Registrado", f"S/ {max_precio:.2f}", help="Meta: Identificar productos con precios elevados")
        c3.metric("Precio Mínimo Registrado", f"S/ {min_precio:.2f}", help="Meta: Identificar productos con precios bajos")
        c4.metric("Variación Promedio", f"S/ {var_promedio:.2f}", help="Meta: Reducir fluctuaciones excesivas")
        
        st.markdown("### Capa Semántica - Datos Filtrados")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

elif pagina == "⑦ Visualización BI":
    st.subheader("Visualización BI")
    if df_filtrado.empty:
        st.warning("No hay datos para graficar con los filtros activos.")
    else:
        avg_precio = df_filtrado["precio_promedio"].mean()
        max_precio = df_filtrado["precio_maximo"].max()
        min_precio = df_filtrado["precio_minimo"].min()
        var_promedio = df_filtrado["variacion_precio"].mean()

        # Fila 1: Tarjetas KPI
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-container" style="border-left: 5px solid #3b82f6;">
                    <span class="kpi-title">Precio Promedio General</span>
                    <h3 class="kpi-val">S/ {avg_precio:.2f}</h3>
                    <span class="kpi-meta">Meta: Mantener estabilidad</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-container" style="border-left: 5px solid #10b981;">
                    <span class="kpi-title">Precio Máximo Registrado</span>
                    <h3 class="kpi-val">S/ {max_precio:.2f}</h3>
                    <span class="kpi-meta">Meta: Identificar precios altos</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-container" style="border-left: 5px solid #8b5cf6;">
                    <span class="kpi-title">Precio Mínimo Registrado</span>
                    <h3 class="kpi-val">S/ {min_precio:.2f}</h3>
                    <span class="kpi-meta">Meta: Identificar precios bajos</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-container" style="border-left: 5px solid #f97316;">
                    <span class="kpi-title">Variación Promedio</span>
                    <h3 class="kpi-val">S/ {var_promedio:.2f}</h3>
                    <span class="kpi-meta">Meta: Reducir fluctuaciones</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Fila 2: Top productos por precio promedio
        top = df_filtrado.groupby("producto", as_index=False)["precio_promedio"].mean().sort_values("precio_promedio", ascending=False).head(10)
        fig_top = px.bar(top, x="producto", y="precio_promedio", labels={"producto": "Producto", "precio_promedio": "Precio Promedio (S/)"})
        fig_top = embellecer_grafico(fig_top, "Top 10 Productos por Precio Promedio", "bar")
        st.plotly_chart(fig_top, use_container_width=True)

        # Fila 3: Comparación mayorista vs minorista, evolución del precio promedio, y ranking
        col_pie, col_line, col_table = st.columns([1, 1.2, 1.8])

        with col_pie:
            canales = df_filtrado.groupby("tipo_venta", as_index=False)["precio_promedio"].mean()
            fig_pie = px.pie(canales, names="tipo_venta", values="precio_promedio")
            fig_pie = embellecer_grafico(fig_pie, "Comparación Mayorista vs Minorista", "pie")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_line:
            evolucion = df_filtrado.groupby("fecha", as_index=False)["precio_promedio"].mean().sort_values("fecha")
            evolucion["fecha_str"] = evolucion["fecha"].dt.strftime("%d-%m-%Y")
            fig_line = px.line(evolucion, x="fecha_str", y="precio_promedio", markers=True, labels={"fecha_str": "Fecha", "precio_promedio": "Precio Promedio (S/)"})
            fig_line = embellecer_grafico(fig_line, "Evolución del Precio Promedio", "line")
            st.plotly_chart(fig_line, use_container_width=True)

        with col_table:
            st.markdown("<h4 style='text-align: center; margin-bottom: 12px; font-weight: 700;'>Ranking de Productos por Precio Promedio</h4>", unsafe_allow_html=True)
            ranking_df = df_filtrado.groupby(["producto", "tipo_venta", "unidad"]).agg({
                "precio_minimo": "min",
                "precio_promedio": "mean",
                "precio_maximo": "max",
                "variacion_precio": "mean"
            }).reset_index().sort_values("precio_promedio", ascending=False)
            
            ranking_df.columns = ["Producto", "Tipo de Venta", "Unidad", "Mínimo (S/)", "Promedio (S/)", "Máximo (S/)", "Variación (S/)"]
            for c in ["Mínimo (S/)", "Promedio (S/)", "Máximo (S/)", "Variación (S/)"]:
                ranking_df[c] = ranking_df[c].map(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
            
            st.dataframe(ranking_df, use_container_width=True, hide_index=True)







