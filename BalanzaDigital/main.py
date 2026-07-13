import os
import sys
import time
import random
import datetime
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# Configurar path de importación
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from productos import *
from balanza import Balanza
import utilidades

# Configurar ruta del CSV de ventas
utilidades.ARCHIVO = os.path.join(BASE_DIR, "ventas.csv")

# Título de la página Streamlit
st.set_page_config(page_title="Balanza Inteligente IoT", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main-title {
        font-size: 38px;
        font-weight: bold;
        color: #38bdf8;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 16px;
        color: #94a3b8;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚖️ BALANZA INTELIGENTE IoT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Simulador interactivo de pesaje en tiempo real con integración a la nube</div>', unsafe_allow_html=True)

# Inicializar Session State
if "selected_product" not in st.session_state:
    st.session_state.selected_product = "Papa"
if "peso" not in st.session_state:
    st.session_state.peso = 0.0
if "precio" not in st.session_state:
    st.session_state.precio = obtener_precio("Papa", "Minorista")
if "total" not in st.session_state:
    st.session_state.total = 0.0
if "canal" not in st.session_state:
    st.session_state.canal = "Minorista"
if "simulando" not in st.session_state:
    st.session_state.simulando = False

# Función de renderizado de imagen de la balanza
def generar_imagen_pantalla(peso, precio, total, producto, canal, mercado, conectado=True):
    base_img_path = os.path.join(BASE_DIR, "balanza.png")
    wifi_img_path = os.path.join(BASE_DIR, "iconos", "wifi.png")
    
    base_img = Image.open(base_img_path).convert("RGBA")
    img = base_img.copy()
    draw = ImageDraw.Draw(img)
    
    x_min, x_max = 252, 948
    y_min, y_max = 120, 552
    x_mid = 560
    
    # Fondos
    draw.rectangle([(x_min, y_min), (x_mid, y_max)], fill="#f8fafc")
    draw.rectangle([(x_mid, y_min), (x_max, y_max)], fill="#090d16")
    
    # Bordes
    draw.rectangle([(x_min, y_min), (x_max, y_max)], outline="#334155", width=3)
    draw.line([(x_mid, y_min), (x_mid, y_max)], fill="#cbd5e1", width=2)
    
    # Cargar fuentes
    f_reg = os.path.join(BASE_DIR, "arial.ttf")
    f_bold = os.path.join(BASE_DIR, "arialbd.ttf")
    
    try:
        font_title = ImageFont.truetype(f_bold, 30)
        font_label = ImageFont.truetype(f_reg, 16)
        font_label_bold = ImageFont.truetype(f_bold, 18)
        font_digital_lg = ImageFont.truetype(f_bold, 68)
        font_digital_sm = ImageFont.truetype(f_bold, 30)
        font_digital_lbl = ImageFont.truetype(f_reg, 14)
    except Exception:
        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
            font_label = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
            font_label_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
            font_digital_lg = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 68)
            font_digital_sm = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
            font_digital_lbl = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
        except Exception:
            font_title = ImageFont.load_default()
            font_label = ImageFont.load_default()
            font_label_bold = ImageFont.load_default()
            font_digital_lg = ImageFont.load_default()
            font_digital_sm = ImageFont.load_default()
            font_digital_lbl = ImageFont.load_default()
            
    info = obtener_info_producto(producto)
    
    if info:
        nombre = producto
        codigo = info.get("codigo", "P-XXX")
        categoria = info.get("categoria", "General")
        img_filename = info.get("imagen", "")
        img_path = os.path.join(BASE_DIR, img_filename)
        
        # Pegar foto del producto en pantalla (izquierda)
        if img_path and os.path.exists(img_path):
            try:
                p_img = Image.open(img_path).convert("RGBA")
                bbox = p_img.getbbox()
                if bbox:
                    p_img = p_img.crop(bbox)
                p_img.thumbnail((180, 180), Image.Resampling.LANCZOS)
                px = 402 - p_img.width // 2
                py = 230 - p_img.height // 2
                img.paste(p_img, (px, py), p_img)
            except Exception as ex:
                pass
                
        # Textos de producto
        draw.text((270, 340), nombre.upper(), fill="#0f172a", font=font_title)
        draw.text((270, 395), "Categoría:", fill="#64748b", font=font_label)
        draw.text((270, 420), categoria, fill="#1e293b", font=font_label_bold)
        draw.text((270, 480), "Código:", fill="#64748b", font=font_label)
        draw.text((365, 480), codigo, fill="#0f172a", font=font_label_bold)
        
    # Pegar icono WiFi
    if conectado and os.path.exists(wifi_img_path):
        try:
            wifi_img = Image.open(wifi_img_path).convert("RGBA")
            wifi_img.thumbnail((24, 24), Image.Resampling.LANCZOS)
            img.paste(wifi_img, (905, 135), wifi_img)
        except Exception:
            pass
            
    # Cabecera digital
    date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    draw.text((590, 135), mercado[:18], fill="#38bdf8", font=font_label_bold)
    draw.text((590, 165), date_str, fill="#64748b", font=font_label)
    
    # Peso
    draw.text((590, 210), "PESO (kg)", fill="#94a3b8", font=font_digital_lbl)
    peso_str = f"{peso:.3f} kg"
    draw.text((590, 230), peso_str, fill="#10b981", font=font_digital_lg)
    
    # Separador
    draw.line([(590, 315), (925, 315)], fill="#1e293b", width=1)
    
    # Precio Unitario
    draw.text((590, 335), "PRECIO / kg", fill="#94a3b8", font=font_digital_lbl)
    precio_str = f"S/. {precio:.2f}"
    draw.text((590, 355), precio_str, fill="#06b6d4", font=font_digital_sm)
    
    # Total
    draw.text((750, 335), "TOTAL A PAGAR", fill="#94a3b8", font=font_digital_lbl)
    total_str = f"S/. {total:.2f}"
    draw.text((750, 355), total_str, fill="#fb923c", font=font_digital_sm)
    
    # Conexión y Canal
    draw.text((590, 500), "🟢 IoT ONLINE", fill="#10b981", font=font_label_bold)
    canal_text = f"CANAL: {canal.upper()}"
    canal_color = "#38bdf8" if canal == "Minorista" else "#a78bfa"
    draw.text((750, 500), canal_text, fill=canal_color, font=font_label_bold)
    
    # Pegar producto en bandeja física de la balanza
    if info:
        img_filename = info.get("imagen", "")
        img_path = os.path.join(BASE_DIR, img_filename)
        if img_path and os.path.exists(img_path):
            try:
                plate_img = Image.open(img_path).convert("RGBA")
                bbox = plate_img.getbbox()
                if bbox:
                    plate_img = plate_img.crop(bbox)
                plate_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                
                px = 600 - plate_img.width // 2
                py = 965 - plate_img.height
                img.paste(plate_img, (px, py), plate_img)
            except Exception:
                pass
                
    return img

# Layout Streamlit: 2 columnas
col_left, col_right = st.columns([5, 7])

with col_left:
    st.subheader("📦 Catálogo de Productos")
    st.session_state.canal = st.radio("Canal de Venta", ["Minorista", "Mayorista"], horizontal=True)
    mercado_seleccionado = st.selectbox("Mercado / Punto de Venta", MERCADOS)
    st.markdown("---")
    
    for prod_name, info in PRODUCTOS_DB.items():
        price = info["precio_mayorista"] if st.session_state.canal == "Mayorista" else info["precio_minorista"]
        c1, c2, c3 = st.columns([2, 5, 3])
        
        img_path = os.path.join(BASE_DIR, info["imagen"])
        if os.path.exists(img_path):
            c1.image(img_path, width=50)
            
        c2.markdown(f"**{prod_name.upper()}** (Cod: {info['codigo']})<br><span style='color:#fb923c; font-size:13px;'>Precio: S/. {price:.2f} / kg</span>", unsafe_allow_html=True)
        
        if c3.button("⚖️ Cargar", key=f"load_{prod_name}"):
            st.session_state.selected_product = prod_name
            st.session_state.precio = price
            st.session_state.peso = 0.0
            st.session_state.total = 0.0
            st.session_state.simulando = True

with col_right:
    st.subheader("⚖️ Visualizador de Balanza")
    scale_placeholder = st.empty()
    
    if st.session_state.simulando:
        st.session_state.simulando = False
        peso_final = round(random.uniform(0.50, 8.00), 3)
        peso_act = 0.0
        
        while peso_act < peso_final:
            peso_act += round(random.uniform(0.15, 0.45), 3)
            if peso_act > peso_final:
                peso_act = peso_final
            total_act = round(peso_act * st.session_state.precio, 2)
            pil_img = generar_imagen_pantalla(
                peso_act, 
                st.session_state.precio, 
                total_act, 
                st.session_state.selected_product, 
                st.session_state.canal, 
                mercado_seleccionado
            )
            scale_placeholder.image(pil_img, use_container_width=True)
            time.sleep(0.05)
            
        st.session_state.peso = peso_final
        st.session_state.total = round(peso_final * st.session_state.precio, 2)
        st.rerun()
    else:
        pil_img = generar_imagen_pantalla(
            st.session_state.peso, 
            st.session_state.precio, 
            st.session_state.total, 
            st.session_state.selected_product, 
            st.session_state.canal, 
            mercado_seleccionado
        )
        scale_placeholder.image(pil_img, use_container_width=True)
        
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    
    if c_btn1.button("⚖️ Simular Peso", use_container_width=True):
        st.session_state.simulando = True
        st.rerun()
        
    if c_btn2.button("💾 Registrar Venta", use_container_width=True):
        if st.session_state.peso <= 0:
            st.error("Realice el pesaje primero.")
        else:
            utilidades.registrar_venta(
                mercado_seleccionado,
                st.session_state.canal,
                st.session_state.selected_product,
                st.session_state.peso,
                st.session_state.precio,
                st.session_state.total
            )
            st.success(f"Venta registrada: {st.session_state.selected_product} ({st.session_state.canal})")
            st.session_state.peso = 0.0
            st.session_state.total = 0.0
            st.rerun()
            
    if c_btn3.button("📡 Enviar IoT", use_container_width=True):
        st.info("Datos IoT transmitidos al servidor en la nube (simulado).")
        
    st.markdown("---")
    st.subheader("📋 Historial de Ventas Recientes")
    
    try:
        df = utilidades.obtener_historial()
        if df.empty:
            st.info("No hay ventas registradas aún.")
        else:
            df_recientes = df.tail(6).iloc[::-1]
            st.dataframe(
                df_recientes,
                use_container_width=True,
                hide_index=True
            )
    except Exception as e:
        st.error(f"Error al leer historial de ventas: {e}")
