CREATE TABLE IF NOT EXISTS ventas_balanza (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP NOT NULL,
    producto VARCHAR(100) NOT NULL,
    unidad_medida_mayorista VARCHAR(50),
    equiv_kg_lt_mayorista NUMERIC,
    mayorista_precio_min NUMERIC,
    mayorista_precio_prom NUMERIC,
    mayorista_precio_max NUMERIC,
    unidad_medida_minorista VARCHAR(50),
    equiv_kg_lt_minorista NUMERIC,
    minorista_precio_min NUMERIC,
    minorista_precio_prom NUMERIC,
    minorista_precio_max NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fecha_producto UNIQUE (fecha, producto)
);
