-- Data Warehouse para Supabase PostgreSQL
-- Ejecutar en Supabase > SQL Editor.

create table if not exists stg_precios_raw (
    id_stg bigserial primary key,
    fecha_registro date,
    fecha_captura timestamptz default now(),
    producto_nombre text,
    unidad_medida text,
    precio_mayorista_orig numeric(18,2),
    precio_minorista_orig numeric(18,2),
    hoja_origen text
);

create table if not exists dim_producto (
    id_producto bigserial primary key,
    producto text not null unique
);

create table if not exists dim_anio (
    id_anio bigserial primary key,
    anio int not null unique
);

create table if not exists dim_mes (
    id_mes bigserial primary key,
    mes int not null,
    nombre_mes text not null,
    id_anio bigint not null references dim_anio(id_anio),
    unique (id_anio, mes)
);

create table if not exists dim_tiempo (
    id_tiempo bigserial primary key,
    fecha date not null unique,
    dia int not null,
    id_mes bigint not null references dim_mes(id_mes)
);

create table if not exists dim_tipo_venta (
    id_tipo_venta bigserial primary key,
    tipo_venta text not null unique
);

create table if not exists dim_unidad (
    id_unidad bigserial primary key,
    unidad text not null,
    equivalencia numeric(18,4),
    id_tipo_venta bigint not null references dim_tipo_venta(id_tipo_venta),
    unique (unidad, id_tipo_venta)
);

create table if not exists fact_precios (
    id_precio bigserial primary key,
    id_producto bigint not null references dim_producto(id_producto),
    id_tiempo bigint not null references dim_tiempo(id_tiempo),
    id_unidad bigint not null references dim_unidad(id_unidad),
    id_tipo_venta bigint not null references dim_tipo_venta(id_tipo_venta),
    precio_min numeric(18,2),
    precio_prom numeric(18,2),
    precio_max numeric(18,2)
);

create table if not exists fact_kpis (
    kpi_key bigserial primary key,
    nombre_kpi text not null,
    valor numeric(18,2),
    meta text,
    fecha_calculo timestamptz default now()
);

create or replace view vw_capa_semantica_bi as
select
    f.id_precio as id_precio,
    p.producto as producto,
    t.fecha as fecha,
    t.dia as dia,
    m.mes as mes,
    m.nombre_mes as nombre_mes,
    a.anio as anio,
    u.unidad as unidad,
    u.equivalencia as equivalencia,
    tv.tipo_venta as tipo_venta,
    f.precio_min as precio_minimo,
    f.precio_prom as precio_promedio,
    f.precio_max as precio_maximo,
    f.precio_max - f.precio_min as variacion_precio
from fact_precios f
join dim_producto p on f.id_producto = p.id_producto
join dim_tiempo t on f.id_tiempo = t.id_tiempo
join dim_mes m on t.id_mes = m.id_mes
join dim_anio a on m.id_anio = a.id_anio
join dim_unidad u on f.id_unidad = u.id_unidad
join dim_tipo_venta tv on f.id_tipo_venta = tv.id_tipo_venta;

create or replace view vw_kpis_precios as
select
    avg(precio_prom) as precio_promedio_general,
    max(precio_max) as precio_maximo_registrado,
    min(precio_min) as precio_minimo_registrado,
    avg(precio_max - precio_min) as variacion_promedio
from fact_precios;

create or replace view vw_ranking_productos as
select
    p.producto,
    avg(f.precio_prom) as precio_promedio,
    row_number() over (order by avg(f.precio_prom) desc) as ranking
from fact_precios f
join dim_producto p on f.id_producto = p.id_producto
group by p.producto;

create or replace view vw_grafico_barras_top10 as
select producto, precio_promedio, ranking
from vw_ranking_productos
order by ranking
limit 10;

create or replace view vw_grafico_circular as
select tipo_venta, avg(precio_promedio) as precio_promedio
from vw_capa_semantica_bi
group by tipo_venta;

create or replace view vw_grafico_lineas as
select fecha, avg(precio_promedio) as precio_promedio
from vw_capa_semantica_bi
group by fecha;
