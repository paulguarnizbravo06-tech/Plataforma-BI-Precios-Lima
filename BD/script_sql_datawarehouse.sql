============================================================================
-- MODELO COPO DE NIEVE - POSTGRESQL
-- =========================================================================

-- Eliminar vistas si existen (en orden de dependencia)
DROP VIEW IF EXISTS VW_GRAFICO_BARRAS_TOP10;
DROP VIEW IF EXISTS VW_RANKING_PRODUCTOS;
DROP VIEW IF EXISTS VW_GRAFICO_CIRCULAR;
DROP VIEW IF EXISTS VW_GRAFICO_LINEAS;
DROP VIEW IF EXISTS VW_PREDICCIONES_PRECIOS;
DROP VIEW IF EXISTS VW_PREDICCION_PRODUCTO_INCREMENTO;
DROP VIEW IF EXISTS VW_PREDICCION_DIFERENCIA_CANALES;
DROP VIEW IF EXISTS VW_CAPA_SEMANTICA_BI;
DROP VIEW IF EXISTS VW_KPIS_PRECIOS;

-- Eliminar tablas si existen (en orden por llaves foráneas)
DROP TABLE IF EXISTS FACT_KPIS;
DROP TABLE IF EXISTS FACT_PRECIOS;
DROP TABLE IF EXISTS DIM_MERCADO;
DROP TABLE IF EXISTS DIM_TIPO_MERCADO;
DROP TABLE IF EXISTS DIM_REGION;
DROP TABLE IF EXISTS DIM_UNIDAD;
DROP TABLE IF EXISTS DIM_TIPO_VENTA;
DROP TABLE IF EXISTS DIM_TIEMPO;
DROP TABLE IF EXISTS DIM_MES;
DROP TABLE IF EXISTS DIM_ANIO;
DROP TABLE IF EXISTS DIM_PRODUCTO;
DROP TABLE IF EXISTS DIM_CATEGORIA;
DROP TABLE IF EXISTS STG_PRECIOS_RAW;

-- ============================================================================
-- CREACIÓN DE TABLAS
-- ============================================================================

CREATE TABLE STG_PRECIOS_RAW (
    id_stg INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_registro DATE NULL,
    fecha_captura TIMESTAMP NULL,
    producto_nombre VARCHAR(150) NULL,
    unidad_medida VARCHAR(80) NULL,
    precio_mayorista_orig DECIMAL(18,2) NULL,
    precio_minorista_orig DECIMAL(18,2) NULL
);

CREATE TABLE DIM_PRODUCTO (
    id_producto INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    producto VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE DIM_ANIO (
    id_anio INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    anio INT NOT NULL UNIQUE
);

CREATE TABLE DIM_MES (
    id_mes INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mes INT NOT NULL,
    nombre_mes VARCHAR(30) NOT NULL,
    id_anio INT NOT NULL,
    CONSTRAINT FK_DIM_MES_ANIO FOREIGN KEY (id_anio) REFERENCES DIM_ANIO(id_anio),
    CONSTRAINT UQ_DIM_MES UNIQUE (id_anio, mes)
);

CREATE TABLE DIM_TIEMPO (
    id_tiempo INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    dia INT NOT NULL,
    id_mes INT NOT NULL,
    CONSTRAINT FK_DIM_TIEMPO_MES FOREIGN KEY (id_mes) REFERENCES DIM_MES(id_mes)
);

CREATE TABLE DIM_TIPO_VENTA (
    id_tipo_venta INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_venta VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE DIM_UNIDAD (
    id_unidad INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unidad VARCHAR(80) NOT NULL,
    equivalencia DECIMAL(18,4) NULL,
    id_tipo_venta INT NOT NULL,
    CONSTRAINT FK_DIM_UNIDAD_TIPO_VENTA FOREIGN KEY (id_tipo_venta) REFERENCES DIM_TIPO_VENTA(id_tipo_venta),
    CONSTRAINT UQ_DIM_UNIDAD UNIQUE (unidad, id_tipo_venta)
);

CREATE TABLE FACT_PRECIOS (
    id_precio INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_producto INT NOT NULL,
    id_tiempo INT NOT NULL,
    id_unidad INT NOT NULL,
    id_tipo_venta INT NOT NULL,
    precio_min DECIMAL(18,2) NULL,
    precio_prom DECIMAL(18,2) NULL,
    precio_max DECIMAL(18,2) NULL,
    CONSTRAINT FK_FACT_PRECIOS_PRODUCTO FOREIGN KEY (id_producto) REFERENCES DIM_PRODUCTO(id_producto),
    CONSTRAINT FK_FACT_PRECIOS_TIEMPO FOREIGN KEY (id_tiempo) REFERENCES DIM_TIEMPO(id_tiempo),
    CONSTRAINT FK_FACT_PRECIOS_UNIDAD FOREIGN KEY (id_unidad) REFERENCES DIM_UNIDAD(id_unidad),
    CONSTRAINT FK_FACT_PRECIOS_TIPO_VENTA FOREIGN KEY (id_tipo_venta) REFERENCES DIM_TIPO_VENTA(id_tipo_venta)
);

-- Índices explícitos (PostgreSQL crea automáticamente los de las PK y UNIQUE)
CREATE INDEX IX_FACT_PRECIOS_PRODUCTO ON FACT_PRECIOS (id_producto);
CREATE INDEX IX_FACT_PRECIOS_TIEMPO ON FACT_PRECIOS (id_tiempo);
CREATE INDEX IX_FACT_PRECIOS_UNIDAD ON FACT_PRECIOS (id_unidad);
CREATE INDEX IX_FACT_PRECIOS_TIPO_VENTA ON FACT_PRECIOS (id_tipo_venta);

-- ============================================================================
-- CREACIÓN DE VISTAS
-- ============================================================================

CREATE OR REPLACE VIEW VW_CAPA_SEMANTICA_BI AS
SELECT
    f.id_precio AS IdPrecio,
    p.producto AS Producto,
    t.fecha AS Fecha,
    t.dia AS Dia,
    m.mes AS Mes,
    m.nombre_mes AS NombreMes,
    a.anio AS Anio,
    u.unidad AS Unidad,
    u.equivalencia AS Equivalencia,
    tv.tipo_venta AS TipoVenta,
    f.precio_min AS PrecioMinimo,
    f.precio_prom AS PrecioPromedio,
    f.precio_max AS PrecioMaximo,
    f.precio_max - f.precio_min AS VariacionPrecio
FROM FACT_PRECIOS f
INNER JOIN DIM_PRODUCTO p ON f.id_producto = p.id_producto
INNER JOIN DIM_TIEMPO t ON f.id_tiempo = t.id_tiempo
INNER JOIN DIM_MES m ON t.id_mes = m.id_mes
INNER JOIN DIM_ANIO a ON m.id_anio = a.id_anio
INNER JOIN DIM_UNIDAD u ON f.id_unidad = u.id_unidad
INNER JOIN DIM_TIPO_VENTA tv ON f.id_tipo_venta = tv.id_tipo_venta;

CREATE OR REPLACE VIEW VW_KPIS_PRECIOS AS
SELECT
    AVG(precio_prom) AS PrecioPromedioGeneral,
    MAX(precio_max) AS PrecioMaximoRegistrado,
    MIN(precio_min) AS PrecioMinimoRegistrado,
    AVG(precio_max - precio_min) AS VariacionPromedio
FROM FACT_PRECIOS;

CREATE OR REPLACE VIEW VW_RANKING_PRODUCTOS AS
SELECT
    p.producto AS Producto,
    AVG(f.precio_prom) AS PrecioPromedio,
    ROW_NUMBER() OVER (ORDER BY AVG(f.precio_prom) DESC) AS Ranking
FROM FACT_PRECIOS f
INNER JOIN DIM_PRODUCTO p ON f.id_producto = p.id_producto
GROUP BY p.producto;

CREATE OR REPLACE VIEW VW_GRAFICO_BARRAS_TOP10 AS
SELECT 
    Producto,
    PrecioPromedio,
    Ranking
FROM VW_RANKING_PRODUCTOS
ORDER BY Ranking
LIMIT 10;

CREATE OR REPLACE VIEW VW_GRAFICO_CIRCULAR AS
SELECT
    TipoVenta,
    AVG(PrecioPromedio) AS PrecioPromedio
FROM VW_CAPA_SEMANTICA_BI
GROUP BY TipoVenta;

CREATE OR REPLACE VIEW VW_GRAFICO_LINEAS AS
SELECT
    Fecha,
    AVG(PrecioPromedio) AS PrecioPromedio
FROM VW_CAPA_SEMANTICA_BI
GROUP BY Fecha;

-- Predicciones lineales a 8 semanas
CREATE OR REPLACE VIEW VW_PREDICCIONES_PRECIOS AS
WITH SERIE AS (
    SELECT
        Fecha,
        (Fecha::date - '2000-01-01'::date) AS X,
        AVG(PrecioPromedio) AS Y,
        AVG(VariacionPrecio) AS VariacionY
    FROM VW_CAPA_SEMANTICA_BI
    GROUP BY Fecha
),
REGRESION AS (
    SELECT
        MAX(Fecha) AS UltimaFecha,
        AVG(CAST(X AS FLOAT)) AS AvgX,
        AVG(CAST(Y AS FLOAT)) AS AvgY,
        AVG(CAST(VariacionY AS FLOAT)) AS AvgVariacionY,
        SUM((X - AvgValores.AvgX) * (Y - AvgValores.AvgY))
            / NULLIF(SUM((X - AvgValores.AvgX) * (X - AvgValores.AvgX)), 0) AS PendientePrecio,
        SUM((X - AvgValores.AvgX) * (VariacionY - AvgValores.AvgVariacionY))
            / NULLIF(SUM((X - AvgValores.AvgX) * (X - AvgValores.AvgX)), 0) AS PendienteVariacion
    FROM SERIE
    CROSS JOIN (
        SELECT
            AVG(CAST(X AS FLOAT)) AS AvgX,
            AVG(CAST(Y AS FLOAT)) AS AvgY,
            AVG(CAST(VariacionY AS FLOAT)) AS AvgVariacionY
        FROM SERIE
    ) AvgValores
    GROUP BY AvgValores.AvgX, AvgValores.AvgY, AvgValores.AvgVariacionY
),
SEMANAS AS (
    SELECT 1 AS Semana UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
)
SELECT
    (UltimaFecha + (Semana * 7))::date AS FechaPrediccion,
    AvgY + PendientePrecio * (
        ((UltimaFecha + (Semana * 7))::date - '2000-01-01'::date) - AvgX
    ) AS PrecioPromedioFuturo,
    AvgVariacionY + PendienteVariacion * (
        ((UltimaFecha + (Semana * 7))::date - '2000-01-01'::date) - AvgX
    ) AS TendenciaVariacion
FROM REGRESION
CROSS JOIN SEMANAS;

CREATE OR REPLACE VIEW VW_PREDICCION_PRODUCTO_INCREMENTO AS
WITH SERIE AS (
    SELECT
        Producto,
        Fecha,
        (Fecha::date - '2000-01-01'::date) AS X,
        AVG(PrecioPromedio) AS Y
    FROM VW_CAPA_SEMANTICA_BI
    GROUP BY Producto, Fecha
),
BASE AS (
    SELECT
        Producto,
        AVG(CAST(X AS FLOAT)) AS AvgX,
        AVG(CAST(Y AS FLOAT)) AS AvgY,
        MAX(X) AS MaxX
    FROM SERIE
    GROUP BY Producto
    HAVING COUNT(*) >= 2
),
REGRESION AS (
    SELECT
        s.Producto,
        b.MaxX,
        MAX(CASE WHEN s.X = b.MaxX THEN s.Y END) AS PrecioActual,
        b.AvgY + (
            SUM((s.X - b.AvgX) * (s.Y - b.AvgY))
            / NULLIF(SUM((s.X - b.AvgX) * (s.X - b.AvgX)), 0)
        ) * ((b.MaxX + 56) - b.AvgX) AS PrecioFuturo
    FROM SERIE s
    INNER JOIN BASE b ON s.Producto = b.Producto
    GROUP BY s.Producto, b.MaxX, b.AvgX, b.AvgY
)
SELECT
    Producto,
    PrecioActual,
    PrecioFuturo,
    PrecioFuturo - PrecioActual AS IncrementoEsperado,
    ROW_NUMBER() OVER (ORDER BY PrecioFuturo - PrecioActual DESC) AS RankingIncremento
FROM REGRESION;

CREATE OR REPLACE VIEW VW_PREDICCION_DIFERENCIA_CANALES AS
WITH SERIE AS (
    SELECT
        Fecha,
        (Fecha::date - '2000-01-01'::date) AS X,
        AVG(CASE WHEN TipoVenta = 'Minorista' THEN PrecioPromedio END)
        - AVG(CASE WHEN TipoVenta = 'Mayorista' THEN PrecioPromedio END) AS Y
    FROM VW_CAPA_SEMANTICA_BI
    GROUP BY Fecha
),
BASE AS (
    SELECT AVG(CAST(X AS FLOAT)) AS AvgX, AVG(CAST(Y AS FLOAT)) AS AvgY, MAX(Fecha) AS UltimaFecha
    FROM SERIE
    WHERE Y IS NOT NULL
),
REGRESION AS (
    SELECT
        b.UltimaFecha,
        b.AvgX,
        b.AvgY,
        SUM((s.X - b.AvgX) * (s.Y - b.AvgY))
        / NULLIF(SUM((s.X - b.AvgX) * (s.X - b.AvgX)), 0) AS Pendiente
    FROM SERIE s
    CROSS JOIN BASE b
    WHERE s.Y IS NOT NULL
    GROUP BY b.UltimaFecha, b.AvgX, b.AvgY
),
SEMANAS AS (
    SELECT 1 AS Semana UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8
)
SELECT
    (UltimaFecha + (Semana * 7))::date AS FechaPrediccion,
    AvgY + Pendiente * (
        ((UltimaFecha + (Semana * 7))::date - '2000-01-01'::date) - AvgX
    ) AS DiferenciaMayoristaMinoristaFutura
FROM REGRESION
CROSS JOIN SEMANAS;

-- ============================================================================
-- TABLA DE KPIs Y PROCEDIMIENTO ALMACENADO
-- ============================================================================

CREATE TABLE FACT_KPIS (
    KPIKey INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    NombreKPI VARCHAR(100) NOT NULL,
    Valor DECIMAL(18,2) NULL,
    Meta VARCHAR(150) NULL,
    FechaCalculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE PROCEDURE SP_REFRESCAR_KPIS()
LANGUAGE plpgsql
AS $$
BEGIN
    -- TRUNCATE remueve todas las filas rápidamente
    TRUNCATE TABLE FACT_KPIS;

    INSERT INTO FACT_KPIS (NombreKPI, Valor, Meta)
    SELECT 'Precio Promedio General', PrecioPromedioGeneral, 'Mantener estabilidad de precios'
    FROM VW_KPIS_PRECIOS
    UNION ALL
    SELECT 'Precio Maximo Registrado', PrecioMaximoRegistrado, 'Identificar precios elevados'
    FROM VW_KPIS_PRECIOS
    UNION ALL
    SELECT 'Precio Minimo Registrado', PrecioMinimoRegistrado, 'Identificar precios bajos'
    FROM VW_KPIS_PRECIOS
    UNION ALL
    SELECT 'Variacion Promedio', VariacionPromedio, 'Monitorear el rango maximo - minimo'
    FROM VW_KPIS_PRECIOS;
END;
$$;

-- ============================================================================
-- EJECUCIÓN Y PRUEBAS
-- ============================================================================

-- Llamar al procedimiento en PostgreSQL se hace con CALL
CALL SP_REFRESCAR_KPIS();

-- Consultas de verificación
SELECT * FROM VW_KPIS_PRECIOS;
SELECT * FROM VW_GRAFICO_BARRAS_TOP10;
SELECT * FROM VW_GRAFICO_CIRCULAR;
SELECT * FROM VW_GRAFICO_LINEAS ORDER BY Fecha;
SELECT * FROM VW_RANKING_PRODUCTOS ORDER BY Ranking;
SELECT * FROM VW_PREDICCIONES_PRECIOS ORDER BY FechaPrediccion;
SELECT * FROM VW_PREDICCION_PRODUCTO_INCREMENTO ORDER BY RankingIncremento LIMIT 10;
SELECT * FROM VW_PREDICCION_DIFERENCIA_CANALES ORDER BY FechaPrediccion;
