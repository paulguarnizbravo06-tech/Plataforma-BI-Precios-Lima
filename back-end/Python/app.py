from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
import pyodbc
from pathlib import Path

# ============================================================
# ESTRUCTURA DEL PROYECTO
# Front-End : templates HTML y recursos de img/
# Back-End  : rutas Flask y control del flujo BI
# BD        : conexion SQL Server y carga Data Warehouse
# Python/ML : ingesta, ETL, analitica y dashboard
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "front-end"
app = Flask(__name__, template_folder=str(FRONTEND_DIR / "html"))


# ============================================================
# FRONT-END: recursos estaticos
# ============================================================
@app.route("/img/<path:filename>")
def img_files(filename):
    return send_from_directory(str(FRONTEND_DIR / "img"), filename)


# ============================================================
# BACK-END: estado global del pipeline BI
# ============================================================
pipeline_status = {
    "fuentes": {"registros": 0, "estado": "Pendiente", "origenes": ["SISAP", "MIDAGRI", "Mi Caserita"]},
    "staging": {"registros": 0, "estado": "Pendiente", "errores": 0, "calidad_check": "No Iniciado"},
    "etl": {"registros": 0, "estado": "Pendiente", "metricas_base": False},
    "dw": {"registros": 0, "estado": "Pendiente",
           "tablas": []},
    "ia": {"estado": "Pendiente", "modelos": ["Regresión", "Series de Tiempo", "Clasificación"], "predicciones": 0},
    "kpis": {"estado": "Pendiente", "medidas_dax": 0, "reglas_negocio": "Pendiente"},
    "dashboard": {"estado": "Pendiente", "filtros_activos": ["Producto", "Mercado", "Distrito", "Fecha"]}
}

staging_data = []
errores_data = []
etl_data = []
dw_data = []
ia_predicciones = []
kpis_calculados = {}
ia_resumen = {}

# Diccionario expandido de series de tiempo para las predicciones a 14 días (Módulo IA)
ia_series_tiempo = {}


# ============================================================
# BD: conexion y funciones auxiliares para SQL Server
# ============================================================
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


def verificar_esquema_dw(cursor):
    """Valida que SQL Server tenga aplicado el modelo copo de nieve vigente."""
    requeridas = {
        "DIM_PRODUCTO": {"id_producto", "producto"},
        "DIM_ANIO": {"id_anio", "anio"},
        "DIM_MES": {"id_mes", "mes", "nombre_mes", "id_anio"},
        "DIM_TIEMPO": {"id_tiempo", "fecha", "dia", "id_mes"},
        "DIM_TIPO_VENTA": {"id_tipo_venta", "tipo_venta"},
        "DIM_UNIDAD": {"id_unidad", "unidad", "equivalencia", "id_tipo_venta"},
        "FACT_PRECIOS": {
            "id_precio", "id_producto", "id_tiempo", "id_unidad",
            "id_tipo_venta", "precio_min", "precio_prom", "precio_max"
        },
        "FACT_KPIS": {"KPIKey", "NombreKPI", "Valor", "Meta", "FechaCalculo"},
        "STG_PRECIOS_RAW": {
            "fecha_registro", "fecha_captura", "producto_nombre",
            "unidad_medida", "precio_mayorista_orig", "precio_minorista_orig"
        }
    }
    for tabla, columnas_requeridas in requeridas.items():
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """, tabla)
        columnas_actuales = {row[0] for row in cursor.fetchall()}
        faltantes = sorted(columnas_requeridas - columnas_actuales)
        if faltantes:
            raise RuntimeError(
                f"El esquema SQL no esta actualizado. Ejecuta script_sql_datawarehouse.sql. "
                f"Faltan columnas en {tabla}: {', '.join(faltantes)}"
            )


def mensaje_error_sql(error):
    texto = str(error)
    if "08001" in texto:
        return (
            "No se pudo abrir SQL Server local .\\SQLEXPRESS. "
            "Verifica que el servicio SQL Server (SQLEXPRESS) este iniciado y ejecuta "
            "la aplicacion con tu usuario de Windows. Detalle: " + texto
        )
    if "SSPI" in texto:
        return (
            "SQL Server respondio, pero Windows no pudo validar la autenticacion integrada (SSPI). "
            "Ejecuta la aplicacion con tu usuario de Windows o configura un login SQL. Detalle: " + texto
        )
    return texto


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


def proyectar_serie(serie, periodos=1):
    """Proyecta el siguiente precio con una tendencia lineal simple y trazable."""
    valores = pd.to_numeric(serie, errors="coerce").dropna().astype(float).tolist()
    if not valores:
        return 0.0
    if len(valores) == 1:
        return valores[0]
    x = np.arange(len(valores), dtype=float)
    pendiente, intercepto = np.polyfit(x, valores, 1)
    return max(0.0, float(intercepto + pendiente * (len(valores) - 1 + periodos)))


def construir_hechos_analiticos(datos):
    """Expande cada fila SISAP en hechos Mayorista y Minorista, como FACT_PRECIOS."""
    filas = []
    for row in datos:
        fecha = pd.to_datetime(row.get("fecha"), errors="coerce")
        producto = str(row.get("producto") or "").strip()
        if pd.isna(fecha) or not producto:
            continue

        ventas = [
            ("Mayorista", "unidad_may", "equiv_may", "may_min", "precio_mayorista", "may_max"),
            ("Minorista", "unidad_min", "equiv_min", "min_min", "precio_minorista", "min_max")
        ]
        for tipo_venta, unidad_col, equiv_col, min_col, prom_col, max_col in ventas:
            precio_prom = pd.to_numeric(row.get(prom_col), errors="coerce")
            if pd.isna(precio_prom):
                continue
            precio_min = pd.to_numeric(row.get(min_col), errors="coerce")
            precio_max = pd.to_numeric(row.get(max_col), errors="coerce")
            filas.append({
                "fecha": fecha,
                "producto": producto,
                "tipo_venta": tipo_venta,
                "unidad": str(row.get(unidad_col) or "Sin unidad").strip(),
                "equivalencia": pd.to_numeric(row.get(equiv_col), errors="coerce"),
                "precio_min": precio_min,
                "precio_prom": precio_prom,
                "precio_max": precio_max,
                "variacion_precio": precio_max - precio_min
                    if pd.notna(precio_max) and pd.notna(precio_min) else np.nan
            })
    return pd.DataFrame(filas)


def calcular_predicciones_dashboard(df):
    """Resume las cuatro predicciones ejecutivas solicitadas a 8 semanas."""
    hechos = construir_hechos_analiticos(df.to_dict(orient="records"))
    series = {}
    for producto, grupo in hechos.groupby("producto"):
        serie = grupo.groupby("fecha")["precio_prom"].mean().sort_index()
        if not serie.empty:
            actual = float(serie.iloc[-1])
            futuro = proyectar_serie(serie, periodos=8)
            series[producto] = {"actual": actual, "futuro": futuro, "incremento": futuro - actual}

    precio_futuro = float(np.mean([x["futuro"] for x in series.values()])) if series else 0.0
    variacion_diaria = hechos.groupby("fecha")["variacion_precio"].mean().sort_index()
    tendencia = proyectar_serie(variacion_diaria, periodos=8)
    mayor_incremento = max(series.items(), key=lambda item: item[1]["incremento"])[0] if series else "Sin datos"

    por_canal = hechos.groupby(["fecha", "tipo_venta"])["precio_prom"].mean().unstack()
    diferencias = (
        por_canal["Minorista"] - por_canal["Mayorista"]
        if {"Mayorista", "Minorista"}.issubset(por_canal.columns) else pd.Series(dtype=float)
    )
    diferencia_futura = proyectar_serie(diferencias.dropna(), periodos=8)
    return {
        "precio_promedio_futuro": round(precio_futuro, 2),
        "tendencia_variacion": round(tendencia, 2),
        "producto_mayor_incremento": mayor_incremento,
        "diferencia_futura_canales": round(diferencia_futura, 2)
    }


def obtener_o_crear_producto(cursor, nombre_producto):
    nombre_producto = (nombre_producto or "Sin producto").strip()
    cursor.execute("SELECT id_producto FROM DIM_PRODUCTO WHERE producto = ?", nombre_producto)
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("""
        INSERT INTO DIM_PRODUCTO (producto)
        OUTPUT INSERTED.id_producto
        VALUES (?)
    """, nombre_producto)
    return cursor.fetchone()[0]


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


def obtener_o_crear_unidad(cursor, unidad, equivalencia, id_tipo_venta):
    unidad = (unidad or "Sin unidad").strip()
    equivalencia = sql_valor(equivalencia)
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


def obtener_o_crear_tiempo(cursor, fecha):
    fecha_dt = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(fecha_dt):
        fecha_dt = pd.Timestamp.today()
    fecha_date = fecha_dt.date()

    cursor.execute("SELECT id_tiempo FROM DIM_TIEMPO WHERE fecha = ?", fecha_date)
    row = cursor.fetchone()
    if row:
        return row[0]

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    cursor.execute("SELECT id_anio FROM DIM_ANIO WHERE anio = ?", int(fecha_dt.year))
    anio_row = cursor.fetchone()
    if anio_row:
        id_anio = anio_row[0]
    else:
        cursor.execute("INSERT INTO DIM_ANIO (anio) OUTPUT INSERTED.id_anio VALUES (?)", int(fecha_dt.year))
        id_anio = cursor.fetchone()[0]

    cursor.execute("SELECT id_mes FROM DIM_MES WHERE id_anio = ? AND mes = ?", id_anio, int(fecha_dt.month))
    mes_row = cursor.fetchone()
    if mes_row:
        id_mes = mes_row[0]
    else:
        cursor.execute("""
            INSERT INTO DIM_MES (mes, nombre_mes, id_anio)
            OUTPUT INSERTED.id_mes
            VALUES (?, ?, ?)
        """, int(fecha_dt.month), meses[int(fecha_dt.month) - 1], id_anio)
        id_mes = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO DIM_TIEMPO (fecha, dia, id_mes)
        OUTPUT INSERTED.id_tiempo
        VALUES (?, ?, ?)
    """, fecha_date, int(fecha_dt.day), id_mes)
    return cursor.fetchone()[0]



# ============================================================
# BACK-END / DW: modelo copo de nieve para visualizacion
# ============================================================
def construir_modelo_copo_nieve_desde_datos():
    """Construye la visualizacion del modelo copo de nieve vigente del DW."""
    fuente = dw_data or etl_data or staging_data
    if not fuente:
        return {
            "hay_datos": False,
            "mensaje": "Primero carga un Excel, valida Staging y ejecuta ETL.",
            "tablas": [],
            "relaciones": [],
            "registros": 0
        }

    def field(name, role=""):
        return {"name": name, "role": role}

    def table(table_id, nombre, tipo, icono, color, x, y, width, fields):
        return {
            "id": table_id,
            "nombre": nombre,
            "tipo": tipo,
            "icono": icono,
            "color": color,
            "x": x,
            "y": y,
            "w": width,
            "h": max(104, 72 + len(fields) * 17),
            "fields": fields
        }

    tablas = [
        table("dim_anio", "DIM_ANIO", "DIM", "calendar-clock", "purple", 80, 70, 180, [
            field("id_anio", "PK"),
            field("anio")
        ]),
        table("dim_mes", "DIM_MES", "DIM", "calendar-range", "purple", 325, 70, 210, [
            field("id_mes", "PK"),
            field("mes"),
            field("nombre_mes"),
            field("id_anio", "FK")
        ]),
        table("dim_tiempo", "DIM_TIEMPO", "DIM", "calendar-days", "purple", 605, 70, 210, [
            field("id_tiempo", "PK"),
            field("fecha"),
            field("dia"),
            field("id_mes", "FK")
        ]),
        table("dim_producto", "DIM_PRODUCTO", "DIM", "package", "blue", 80, 350, 220, [
            field("id_producto", "PK"),
            field("producto")
        ]),
        table("fact_precios", "FACT_PRECIOS", "FACT", "database", "amber", 490, 315, 280, [
            field("id_precio", "PK"),
            field("id_producto", "FK"),
            field("id_tiempo", "FK"),
            field("id_unidad", "FK"),
            field("id_tipo_venta", "FK"),
            field("precio_min", "MEDIDA"),
            field("precio_prom", "MEDIDA"),
            field("precio_max", "MEDIDA")
        ]),
        table("dim_unidad", "DIM_UNIDAD", "DIM", "scale", "cyan", 940, 350, 230, [
            field("id_unidad", "PK"),
            field("unidad"),
            field("equivalencia"),
            field("id_tipo_venta", "FK")
        ]),
        table("dim_tipo_venta", "DIM_TIPO_VENTA", "DIM", "badge-dollar-sign", "emerald", 940, 590, 230, [
            field("id_tipo_venta", "PK"),
            field("tipo_venta")
        ])
    ]

    relaciones = [
        {"from": "dim_anio", "to": "dim_mes", "label": "1:N", "color": "purple", "path": "M 260 120 H 325", "lx": 292, "ly": 120},
        {"from": "dim_mes", "to": "dim_tiempo", "label": "1:N", "color": "purple", "path": "M 535 135 H 605", "lx": 570, "ly": 135},
        {"from": "dim_tiempo", "to": "fact_precios", "label": "1:N", "color": "amber", "path": "M 710 210 V 260 H 630 V 315", "lx": 710, "ly": 260},
        {"from": "dim_producto", "to": "fact_precios", "label": "1:N", "color": "amber", "path": "M 300 405 H 395 V 405 H 490", "lx": 395, "ly": 405},
        {"from": "dim_unidad", "to": "fact_precios", "label": "1:N", "color": "amber", "path": "M 940 405 H 855 V 405 H 770", "lx": 855, "ly": 405},
        {"from": "dim_tipo_venta", "to": "dim_unidad", "label": "1:N", "color": "emerald", "path": "M 1055 590 V 490", "lx": 1055, "ly": 540},
        {"from": "dim_tipo_venta", "to": "fact_precios", "label": "1:N", "color": "emerald", "path": "M 940 640 H 845 V 555 H 770", "lx": 845, "ly": 555}
    ]

    return {
        "hay_datos": True,
        "mensaje": "Modelo copo de nieve actualizado segun el esquema fisico del Data Warehouse.",
        "tablas": tablas,
        "relaciones": relaciones,
        "registros": len(fuente)
    }


# ============================================================
# FRONT-END: pantalla general
# ============================================================
@app.route("/")
def home():
    return render_template("index.html", status=pipeline_status)


# ============================================================
# PYTHON: ingesta y normalizacion de datos
# ============================================================
def obtener_datos(archivo):
    """
    Lee SOLO datos reales desde Excel o CSV.
    No rellena precios faltantes con 0 porque eso distorsiona el dashboard.
    Soporta archivos con 12 columnas como Abril.xlsx y también hojas con 7 columnas.
    """
    try:
        def preparar_raw(raw, origen):
            if raw.empty:
                return None

            # Detectar fila inicial de datos: primera fila donde la columna 0 parece fecha.
            fecha_col = pd.to_datetime(raw.iloc[:, 0], errors="coerce", dayfirst=True, format="mixed")
            idx_validos = fecha_col[fecha_col.notna()].index
            if len(idx_validos) == 0:
                return None

            inicio = int(idx_validos.min())
            df = raw.iloc[inicio:].copy()

            # Asegurar mínimo 12 columnas para mantener el esquema completo.
            for c in range(df.shape[1], 12):
                df[c] = np.nan
            df = df.iloc[:, :12]
            df.columns = [
                "fecha", "producto", "unidad_may", "equiv_may", "may_min", "may_prom", "may_max",
                "unidad_min", "equiv_min", "min_min", "min_prom", "min_max"
            ]
            df["hoja_origen"] = origen
            return df

        partes = []
        filename = (getattr(archivo, "filename", "") or "").lower()

        if filename.endswith(".csv"):
            try:
                raw = pd.read_csv(
                    archivo, header=None, names=range(12), sep=";",
                    engine="python", encoding="utf-8-sig"
                )
            except Exception:
                archivo.seek(0)
                raw = pd.read_csv(
                    archivo, header=None, names=range(12), sep=None,
                    engine="python", encoding="utf-8-sig"
                )
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
        df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
        df["producto"] = df["producto"].astype(str).str.strip()

        # Conversiones numéricas reales. Se mantiene NaN si el Excel no trae el dato.
        for col in ["may_min", "may_prom", "may_max", "min_min", "min_prom", "min_max", "equiv_may", "equiv_min"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["precio_mayorista"] = df["may_prom"]
        df["precio_minorista"] = df["min_prom"]

        # Precio de análisis: usa minorista si existe; si no, mayorista.
        # Esto evita inventar minorista cuando el archivo solo tiene mayorista.
        df["precio_analisis"] = df["precio_minorista"].combine_first(df["precio_mayorista"])
        df["tipo_precio"] = np.where(df["precio_minorista"].notna(), "Minorista", "Mayorista")

        df["estado"] = "OK"
        df["error"] = ""
        df.loc[df["producto"].str.len() < 3, "error"] += "Nombre producto inválido | "
        df.loc[df["precio_analisis"].isna() | (df["precio_analisis"] <= 0), "error"] += "Sin precio válido en Excel | "
        df.loc[df["error"] != "", "estado"] = "ERROR"

        cols = [
            "fecha", "producto", "unidad_may", "equiv_may", "may_min", "may_max",
            "unidad_min", "equiv_min", "min_min", "min_max", "precio_mayorista", "precio_minorista",
            "precio_analisis", "tipo_precio", "hoja_origen", "estado", "error"
        ]
        return df[cols]
    except Exception as e:
        print("Error Ingesta:", e)
        return pd.DataFrame()


# ============================================================
# BACK-END: paso 1 - fuentes de datos
# ============================================================
@app.route("/fuentes", methods=["GET", "POST"])
def fuentes():
    global staging_data, errores_data
    data_vista = []
    mensaje = ""

    if request.method == "POST":
        archivo = request.files.get("archivo")
        if archivo:
            df = obtener_datos(archivo)
            if not df.empty:
                df_ok = df[df["estado"] == "OK"]
                df_error = df[df["estado"] == "ERROR"]

                staging_data = df_ok.to_dict(orient="records")
                errores_data = df_error.to_dict(orient="records")
                data_vista = df.to_dict(orient="records")

                pipeline_status["fuentes"] = {"registros": len(df), "estado": "Ingestado",
                                              "origenes": ["SISAP", "MIDAGRI"]}
                pipeline_status["staging"] = {"registros": len(df_ok), "estado": "Listo para Validación",
                                              "errores": len(df_error), "calidad_check": "Pendiente"}
                mensaje = f"✓ {len(df_ok)} Registros listos. {len(df_error)} Enviados a logs de error."
    return render_template("fuentes.html", data=data_vista, mensaje=mensaje)


# ============================================================
# BACK-END: paso 2 - staging area
# ============================================================
@app.route("/staging")
def staging():
    return render_template("staging.html", data=staging_data, errores=errores_data, status=pipeline_status["staging"])


@app.route("/guardar_staging", methods=["POST"])
def guardar_staging():
    pipeline_status["staging"]["calidad_check"] = "Pasó Control de Calidad"
    pipeline_status["staging"]["estado"] = "Tablas Temporales Almacenadas"
    pipeline_status["etl"]["estado"] = "Listo para Transformación"
    return jsonify({"success": True, "msg": "Staging completado. Datos crudos validados y estructurados."})


# ============================================================
# BACK-END / PYTHON: paso 3 - proceso ETL
# ============================================================
@app.route("/etl_page")
def etl_page():
    return render_template("etl.html", data=etl_data, status=pipeline_status["etl"])


@app.route("/ejecutar_etl", methods=["POST"])
def ejecutar_etl():
    global staging_data, etl_data
    if not staging_data:
        return jsonify({"success": False, "msg": "No existen datos limpios en Staging."})

    df = pd.DataFrame(staging_data)
    for col in ["precio_mayorista", "precio_minorista", "precio_analisis"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Metricas alineadas con la sesion 7: promedio de canales y rango maximo-minimo.
    df["precio_unitario"] = df[["precio_mayorista", "precio_minorista"]].mean(axis=1)
    df["diferencia_precio"] = df["precio_minorista"] - df["precio_mayorista"]
    rangos = pd.concat([
        pd.to_numeric(df["may_max"], errors="coerce") - pd.to_numeric(df["may_min"], errors="coerce"),
        pd.to_numeric(df["min_max"], errors="coerce") - pd.to_numeric(df["min_min"], errors="coerce")
    ], axis=1)
    df["variacion_precio"] = rangos.mean(axis=1)
    df = df.replace([np.inf, -np.inf], np.nan)

    etl_data = df.to_dict(orient="records")
    pipeline_status["etl"]["estado"] = "Transformado Exitosamente"
    pipeline_status["etl"]["registros"] = len(etl_data)
    pipeline_status["etl"]["metricas_base"] = True
    pipeline_status["dw"]["estado"] = "Esperando Carga Estructurada"

    return jsonify({"success": True, "msg": "ETL finalizado usando solo valores reales del Excel."})

# ============================================================
# BACK-END / BD: paso 4 - Data Warehouse copo de nieve
# ============================================================
@app.route("/dw")
def dw():
    modelo_dw = construir_modelo_copo_nieve_desde_datos()
    return render_template("dw.html", data=dw_data, status=pipeline_status["dw"], modelo=modelo_dw)


@app.route("/cargar_dw", methods=["POST"])
def cargar_dw():
    global etl_data, dw_data
    if not etl_data:
        return jsonify({"success": False, "msg": "Realice el paso 3 (ETL) primero."})

    conn = None
    try:
        conn = conectar_sql()
        cursor = conn.cursor()
        verificar_esquema_dw(cursor)
        cursor.execute("DELETE FROM FACT_PRECIOS")
        cursor.execute("DELETE FROM STG_PRECIOS_RAW")
        insertados = 0

        for row in etl_data:
            fecha = sql_valor(row.get("fecha"))
            producto = sql_valor(row.get("producto"))
            unidad_staging = sql_valor(row.get("unidad_min")) or sql_valor(row.get("unidad_may")) or "Sin unidad"
            precio_mayorista = sql_valor(row.get("precio_mayorista"))
            precio_minorista = sql_valor(row.get("precio_minorista"))

            cursor.execute("""
                INSERT INTO STG_PRECIOS_RAW
                (fecha_registro, fecha_captura, producto_nombre, unidad_medida,
                 precio_mayorista_orig, precio_minorista_orig)
                VALUES (?, GETDATE(), ?, ?, ?, ?)
            """, fecha, producto, unidad_staging, precio_mayorista, precio_minorista)

            id_producto = obtener_o_crear_producto(cursor, producto)
            id_tiempo = obtener_o_crear_tiempo(cursor, fecha)
            ventas = [
                ("Mayorista", row.get("unidad_may"), row.get("equiv_may"),
                 row.get("may_min"), row.get("precio_mayorista"), row.get("may_max")),
                ("Minorista", row.get("unidad_min"), row.get("equiv_min"),
                 row.get("min_min"), row.get("precio_minorista"), row.get("min_max"))
            ]

            for tipo_venta, unidad, equivalencia, precio_min, precio_prom, precio_max in ventas:
                precio_prom = sql_valor(precio_prom)
                if precio_prom is None:
                    continue

                id_tipo_venta = obtener_o_crear_tipo_venta(cursor, tipo_venta)
                id_unidad = obtener_o_crear_unidad(cursor, unidad, equivalencia, id_tipo_venta)
                cursor.execute("""
                    INSERT INTO FACT_PRECIOS
                    (id_producto, id_tiempo, id_unidad, id_tipo_venta,
                     precio_min, precio_prom, precio_max)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                id_producto, id_tiempo, id_unidad, id_tipo_venta,
                sql_valor(precio_min), precio_prom, sql_valor(precio_max))
                insertados += 1

        cursor.execute("EXEC SP_REFRESCAR_KPIS")
        conn.commit()
        cursor.close()
        conn.close()

        dw_data = etl_data.copy()
        pipeline_status["dw"]["estado"] = "Datos guardados en SQL Server"
        pipeline_status["dw"]["registros"] = insertados
        pipeline_status["dw"]["tablas"] = [
            t["nombre"] for t in construir_modelo_copo_nieve_desde_datos().get("tablas", [])
        ]
        pipeline_status["ia"]["estado"] = "Listo para Correr Modelos"
        return jsonify({
            "success": True,
            "msg": f"Data Warehouse cargado correctamente. Filas insertadas: {insertados}"
        })

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"success": False, "msg": f"Error al guardar en SQL Server: {mensaje_error_sql(e)}"})



# ============================================================
# PYTHON / ML: paso 5 - analitica
# ============================================================
@app.route("/ia")
def ia():
    return render_template("ia.html", data=ia_predicciones, resumen=ia_resumen, status=pipeline_status["ia"])


@app.route("/entrenar_ia", methods=["POST"])
def entrenar_ia():
    global dw_data, ia_predicciones, ia_series_tiempo, ia_resumen
    if not dw_data:
        return jsonify({"success": False, "msg": "Falta poblar el Data Warehouse."})

    df = construir_hechos_analiticos(dw_data)

    predicciones = []
    ia_series_tiempo = {"fechas": []}

    if df.empty:
        ia_predicciones = []
        return jsonify({"success": False, "msg": "No hay datos válidos para analizar."})

    top_productos = df.groupby("producto")["precio_prom"].count().sort_values(ascending=False).head(10).index.tolist()
    fechas = sorted(df["fecha"].dt.strftime("%d %b").unique().tolist())
    ia_series_tiempo["fechas"] = fechas

    for prod in top_productos:
        serie = (df[df["producto"] == prod]
                 .groupby("fecha")["precio_prom"]
                 .mean()
                 .sort_index())
        actual = float(serie.iloc[-1])
        anterior = float(serie.iloc[-2]) if len(serie) >= 2 else actual
        variacion = ((actual - anterior) / anterior * 100) if anterior else 0.0
        predicho = proyectar_serie(serie, periodos=8)

        predicciones.append({
            "producto": prod,
            "precio_actual": round(actual, 2),
            "precio_predicho": round(predicho, 2),
            "alerta": "Alza esperada >10%" if actual and ((predicho - actual) / actual * 100) > 10 else "Normal",
            "confianza": "Regresion lineal a 8 semanas"
        })
        ia_series_tiempo[prod.lower()] = [round(float(x), 2) for x in serie.tolist()]

    ia_predicciones = predicciones
    ia_resumen = calcular_predicciones_dashboard(pd.DataFrame(dw_data))
    pipeline_status["ia"]["estado"] = "Análisis real calculado"
    pipeline_status["ia"]["predicciones"] = len(ia_predicciones)
    pipeline_status["kpis"]["estado"] = "Datos reales listos para KPIs"
    return jsonify({"success": True, "msg": "Predicciones a 8 semanas calculadas con regresion lineal."})

# ============================================================
# BACK-END: paso 6 - capa semantica y KPIs
# ============================================================
@app.route("/kpis")
def kpis():
    return render_template("kpis.html", kpis=kpis_calculados, status=pipeline_status["kpis"])


@app.route("/generar_capa_semantica", methods=["POST"])
def generar_capa_semantica():
    global dw_data, kpis_calculados
    if not dw_data:
        return jsonify({"success": False, "msg": "Data Warehouse vacío. Realice los pasos previos."})

    hechos = construir_hechos_analiticos(dw_data)
    if hechos.empty:
        return jsonify({"success": False, "msg": "No hay precios validos para calcular KPIs."})
    precio_prom = float(hechos["precio_prom"].mean())
    precio_max = float(hechos["precio_max"].max())
    precio_min = float(hechos["precio_min"].min())
    var_promedio = float(hechos["variacion_precio"].mean())

    kpis_calculados = {
        "precio_promedio_general": round(precio_prom, 2),
        "precio_maximo_registrado": round(precio_max, 2),
        "precio_minimo_registrado": round(precio_min, 2),
        "variacion_promedio": round(var_promedio, 2),
        "total_productos_catalogados": int(hechos["producto"].nunique())
    }

    pipeline_status["kpis"]["estado"] = "Catálogo calculado con datos reales"
    pipeline_status["kpis"]["medidas_dax"] = 4
    pipeline_status["kpis"]["reglas_negocio"] = "Datos validados"
    pipeline_status["dashboard"]["estado"] = "Listo para Visualización"

    return jsonify({"success": True, "msg": "Capa Semántica procesada con datos validados."})

# ============================================================
# FRONT-END / PYTHON: paso 7 - dashboard ejecutivo
# ============================================================
@app.route("/dashboard")
def dashboard():
    global dw_data, kpis_calculados, ia_series_tiempo
    if not dw_data or not kpis_calculados:
        return render_template("dashboard.html", data_listos=False)

    df = pd.DataFrame(dw_data)
    hechos = construir_hechos_analiticos(dw_data)
    if hechos.empty:
        return render_template("dashboard.html", data_listos=False)

    resumen = (hechos.groupby("producto")["precio_prom"]
                 .mean()
                 .reset_index()
                 .sort_values("precio_prom", ascending=False)
                 .head(10))
    productos_labels = resumen["producto"].tolist()
    canales = hechos.groupby("tipo_venta")["precio_prom"].mean().to_dict()
    cat_labels = list(canales.keys())
    cat_valores = [round(x, 2) for x in canales.values()]

    evo = hechos.groupby("fecha")["precio_prom"].mean().sort_index()
    evolucion_labels = evo.index.strftime("%d %b").tolist()
    evolucion_precios = [round(float(x), 2) for x in evo.tolist()]

    ranking_base = (hechos.groupby("producto")["precio_prom"]
                      .mean()
                      .sort_values(ascending=False)
                      .head(10)
                      .reset_index())
    ranking_mercados = []
    for i, row in ranking_base.iterrows():
        ranking_mercados.append({
            "ranking": i + 1,
            "mercado": row["producto"],
            "tipo": "Mayorista / Minorista",
            "precio": round(float(row["precio_prom"]), 2),
            "variacion": round(float(hechos[hechos["producto"] == row["producto"]]["variacion_precio"].dropna().mean()), 2)
                         if hechos[hechos["producto"] == row["producto"]]["variacion_precio"].notna().any() else 0.0
        })

    fecha_min = hechos["fecha"].min().strftime("%d/%m/%Y")
    fecha_max = hechos["fecha"].max().strftime("%d/%m/%Y")
    fecha_min_iso = hechos["fecha"].min().strftime("%Y-%m-%d")
    fecha_max_iso = hechos["fecha"].max().strftime("%Y-%m-%d")

    registros_dashboard = []
    for _, row in hechos.iterrows():
        registros_dashboard.append({
            "fecha": row["fecha"].strftime("%Y-%m-%d") if pd.notna(row["fecha"]) else "",
            "producto": str(row.get("producto") or "Sin producto").strip(),
            "tipo_precio": str(row.get("tipo_venta") or "No especificado").strip(),
            "unidad": str(row.get("unidad") or "Sin unidad").strip(),
            "precio_mayorista": round(float(row["precio_prom"]), 2) if row["tipo_venta"] == "Mayorista" else None,
            "precio_minorista": round(float(row["precio_prom"]), 2) if row["tipo_venta"] == "Minorista" else None,
            "precio_analisis": round(float(row["precio_prom"]), 2),
            "precio_min": None if pd.isna(row.get("precio_min")) else round(float(row.get("precio_min")), 2),
            "precio_max": None if pd.isna(row.get("precio_max")) else round(float(row.get("precio_max")), 2),
            "variacion_precio": None if pd.isna(row.get("variacion_precio")) else round(float(row.get("variacion_precio")), 2)
        })

    graficos_data = {
        "productos_labels": productos_labels,
        "cat_labels": cat_labels,
        "cat_valores": cat_valores,
        "evolucion_labels": evolucion_labels,
        "evolucion_precios": evolucion_precios,
        "ranking_mercados": ranking_mercados,
        "fecha_min": fecha_min,
        "fecha_max": fecha_max,
        "fecha_min_iso": fecha_min_iso,
        "fecha_max_iso": fecha_max_iso,
        "productos_filtro": sorted(hechos["producto"].dropna().astype(str).str.strip().unique().tolist()),
        "tipos_filtro": sorted(hechos["tipo_venta"].dropna().astype(str).str.strip().unique().tolist()),
        "unidades_filtro": sorted(hechos["unidad"].fillna("Sin unidad").astype(str).str.strip().unique().tolist()),
        "registros": registros_dashboard
    }

    return render_template(
        "dashboard.html",
        data_listos=True,
        kpis=kpis_calculados,
        graficos=graficos_data,
        predicciones=calcular_predicciones_dashboard(df)
    )

if __name__ == "__main__":
    app.run(debug=True)
