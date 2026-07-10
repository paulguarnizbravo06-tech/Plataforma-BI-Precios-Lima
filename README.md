# Plataforma BI Precios Lima

Proyecto BI para analisis de precios de mercados de Lima con arquitectura cloud:

```text
GitHub -> Streamlit Community Cloud -> Supabase PostgreSQL
                    ^
                    |
              Google Colab
```

## Estructura principal

- `streamlit_app.py`: aplicacion web cloud para Streamlit.
- `BD/script_supabase_postgresql.sql`: modelo Data Warehouse para Supabase PostgreSQL.
- `BD/script_sql_datawarehouse.sql`: version local original para SQL Server.
- `ML/predicciones_sisap_colab.py`: script analitico para Colab.
- `colab/run_from_github.py`: guia minima para llamar el repo desde Colab.
- `back-end/` y `front-end/`: aplicacion Flask/HTML original local.

## 1. Supabase

1. Crear un proyecto en Supabase.
2. Abrir `SQL Editor`.
3. Ejecutar el contenido de:

```text
BD/script_supabase_postgresql.sql
```

4. Copiar la cadena de conexion PostgreSQL.

Formato recomendado para Streamlit:

```text
postgresql+psycopg2://postgres:TU_PASSWORD@TU_HOST:5432/postgres?sslmode=require
```

## 2. Streamlit Community Cloud

1. Entrar a Streamlit Community Cloud.
2. Crear una app desde este repositorio GitHub.
3. Seleccionar:

```text
Main file path: streamlit_app.py
```

4. En `Settings > Secrets`, agregar:

```toml
DATABASE_URL = "postgresql+psycopg2://postgres:TU_PASSWORD@TU_HOST:5432/postgres?sslmode=require"
```

5. Desplegar la app.

## 3. Google Colab

Colab debe llamar el codigo desde GitHub, no copiar todo manualmente:

```python
!git clone https://github.com/paulguarnizbravo06-tech/Plataforma-BI-Precios-Lima.git
%cd Plataforma-BI-Precios-Lima
!pip install -r requirements.txt
!python colab/run_from_github.py
```

La web final se ejecuta en Streamlit Community Cloud. Colab queda para pruebas,
analitica y ejecucion de scripts desde el repositorio.

## 4. Flujo de uso

1. Subir Excel o CSV SISAP desde Streamlit.
2. Validar Staging y ETL.
3. Guardar el Data Warehouse en Supabase.
4. Consultar KPIs, graficos y predicciones desde el dashboard web.
