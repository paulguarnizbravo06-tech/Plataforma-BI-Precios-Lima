# ==========================================
# interfaz.py
# Interfaz gráfica de la balanza IoT con arrastrar y soltar (Drag & Drop)
# y soporte para canales Minoristas y Mayoristas
# ==========================================

import os
import datetime
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont

from productos import *
from balanza import Balanza
from utilidades_balanza import *

# Configuración del tema visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Interfaz:

    def __init__(self):
        self.balanza = Balanza()
        self.peso = 0.0
        self.precio = 0.0
        self.total = 0.0
        
        # Canal de venta por defecto
        self.canal = "Minorista"
        
        # Estado de arrastre
        self.arrastrando = False
        self.producto_arrastrado = None
        self.drag_window = None
        
        # Cargar plantilla de la balanza
        self.base_img_path = "balanza.png"
        if not os.path.exists(self.base_img_path):
            self.base_img_path = os.path.abspath("balanza.png")
            
        self.base_img = Image.open(self.base_img_path).convert("RGBA")
        
        # Inicializar ventana
        self.ventana = ctk.CTk()
        self.ventana.title("Balanza Inteligente IoT - Dashboard Interactiva")
        self.ventana.geometry("1240x740")
        self.ventana.resizable(False, False)
        
        # Crear componentes (3 columnas)
        self.crear_componentes()
        
        # Cargar datos iniciales
        self.actualizar_producto_seleccionado(self.comboProducto.get())
        self.cargar_tabla_ventas()
        
        self.ventana.mainloop()

    def generar_imagen_pantalla(self, conectado=True):
        """
        Dibuja dinámicamente la pantalla sobre balanza.png.
        Muestra la información de pesaje o una guía visual si se está arrastrando.
        """
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        
        # Coordenadas exactas de la pantalla digital (dentro del bisel físico) de balanza.png
        x_min, x_max = 309, 935
        y_min, y_max = 147, 552
        x_mid = 590
        
        # Cargar fuentes desde el directorio local para consistencia en la nube
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        f_reg = os.path.join(BASE_DIR, "arial.ttf")
        f_bold = os.path.join(BASE_DIR, "arialbd.ttf")
        
        try:
            font_title = ImageFont.truetype(f_bold, 26) # Nombre producto
            font_label = ImageFont.truetype(f_reg, 15)   # Etiquetas secundarias
            font_label_bold = ImageFont.truetype(f_bold, 16) # Contenido secundario negrita
            font_digital_lg = ImageFont.truetype(f_bold, 56) # Peso digital grande
            font_digital_sm = ImageFont.truetype(f_bold, 26) # Precios digital mediano
            font_digital_lbl = ImageFont.truetype(f_reg, 13)  # Etiquetas pantalla digital
            font_drag_lg = ImageFont.truetype(f_bold, 32)   # Texto de arrastrar grande
            font_drag_sm = ImageFont.truetype(f_reg, 18)     # Texto de arrastrar chico
        except Exception as e:
            try:
                font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
                font_label = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
                font_label_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)
                font_digital_lg = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
                font_digital_sm = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
                font_digital_lbl = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
                font_drag_lg = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 32)
                font_drag_sm = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
            except Exception:
                font_title = ImageFont.load_default()
                font_label = ImageFont.load_default()
                font_label_bold = ImageFont.load_default()
                font_digital_lg = ImageFont.load_default()
                font_digital_sm = ImageFont.load_default()
                font_digital_lbl = ImageFont.load_default()
                font_drag_lg = ImageFont.load_default()
                font_drag_sm = ImageFont.load_default()

        # --- CASO A: ARRASTRANDO UN PRODUCTO (MOSTRAR TARGET DE DROP) ---
        if self.arrastrando:
            # Fondo completo azul oscuro/glowing
            draw.rectangle([(x_min, y_min), (x_max, y_max)], fill="#0f172a")
            # Borde de zona de soltado en color cian brillante (neon)
            draw.rectangle([(x_min + 15, y_min + 15), (x_max - 15, y_max - 15)], outline="#22d3ee", width=5)
            
            # Centro de la pantalla
            center_x = (x_min + x_max) // 2
            
            # Texto principal
            txt_principal = "📥 DEPOSITAR AQUÍ"
            draw.text((center_x - 130, 240), txt_principal, fill="#22d3ee", font=font_drag_lg)
            
            # Nombre del producto arrastrado
            txt_prod = f"Cargar: {self.producto_arrastrado.upper()}"
            draw.text((center_x - 90, 310), txt_prod, fill="#ffffff", font=font_drag_sm)
            
            # Subtexto
            txt_ayuda = "Suelte el ratón sobre la balanza para pesar"
            draw.text((center_x - 180, 360), txt_ayuda, fill="#94a3b8", font=font_label)
            
            # Estado del sistema
            draw.text((center_x - 65, 480), "MODO DETECCIÓN", fill="#fb923c", font=font_label_bold)
            
            return img

        # --- CASO B: PANTALLA NORMAL ---
        # 1. Dibujar Fondos de las Secciones
        draw.rectangle([(x_min, y_min), (x_mid, y_max)], fill="#f8fafc") # Detalle del Producto (blanco)
        draw.rectangle([(x_mid, y_min), (x_max, y_max)], fill="#090d16") # Pantalla digital (azul oscuro)
        
        # Bordes y división
        draw.rectangle([(x_min, y_min), (x_max, y_max)], outline="#334155", width=3)
        draw.line([(x_mid, y_min), (x_mid, y_max)], fill="#cbd5e1", width=2)
        
        producto = self.comboProducto.get()
        info = obtener_info_producto(producto)
        
        if info:
            nombre = producto
            codigo = info.get("codigo", "P-XXX")
            categoria = info.get("categoria", "General")
            img_path = info.get("imagen", "")
            
            # Cargar y pegar la foto del producto en la pantalla (izquierda)
            if img_path and os.path.exists(img_path):
                try:
                    p_img = Image.open(img_path).convert("RGBA")
                    # Recortar bordes transparentes para centrado exacto
                    bbox = p_img.getbbox()
                    if bbox:
                        p_img = p_img.crop(bbox)
                    p_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                    # Centro horizontal de la sección izquierda (309 a 590 es X=449)
                    px = 449 - p_img.width // 2
                    py = 233 - p_img.height // 2 # Centro vertical entre Y=147 e Y=320
                    img.paste(p_img, (px, py), p_img)
                except Exception as ex:
                    print(f"Error al cargar la imagen del producto en pantalla: {ex}")
            
            # Textos del producto a la izquierda (X=324)
            draw.text((324, 340), nombre.upper(), fill="#0f172a", font=font_title)
            draw.text((324, 395), "Categoría:", fill="#64748b", font=font_label)
            draw.text((324, 420), categoria, fill="#1e293b", font=font_label_bold)
            draw.text((324, 480), "Código:", fill="#64748b", font=font_label)
            draw.text((399, 480), codigo, fill="#0f172a", font=font_label_bold)
            
        # Pegar icono WiFi en la esquina superior derecha
        if conectado and os.path.exists("iconos/wifi.png"):
            try:
                wifi_img = Image.open("iconos/wifi.png").convert("RGBA")
                wifi_img.thumbnail((24, 24), Image.Resampling.LANCZOS)
                img.paste(wifi_img, (895, 162), wifi_img)
            except Exception as ex:
                print(f"Error al cargar wifi icon: {ex}")
                
        # Cabecera digital (X=610)
        mercado = self.comboMercado.get()
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        draw.text((610, 160), mercado[:16], fill="#38bdf8", font=font_label_bold)
        draw.text((610, 190), date_str, fill="#64748b", font=font_label)
        
        # 1. Peso
        draw.text((610, 230), "PESO (kg)", fill="#94a3b8", font=font_digital_lbl)
        peso_str = f"{self.peso:.3f} kg"
        draw.text((610, 250), peso_str, fill="#10b981", font=font_digital_lg)
        
        # Separador horizontal (de 610 a 915)
        draw.line([(610, 335), (915, 335)], fill="#1e293b", width=1)
        
        # 2. Precio Unitario
        draw.text((610, 350), "PRECIO / kg", fill="#94a3b8", font=font_digital_lbl)
        precio_str = f"S/. {self.precio:.2f}"
        draw.text((610, 370), precio_str, fill="#06b6d4", font=font_digital_sm)
        
        # 3. Total
        draw.text((750, 350), "TOTAL A PAGAR", fill="#94a3b8", font=font_digital_lbl)
        total_str = f"S/. {self.total:.2f}"
        draw.text((750, 370), total_str, fill="#fb923c", font=font_digital_sm)
        
        # Estado de conexión y Canal de venta
        draw.text((610, 500), "🟢 IoT ONLINE", fill="#10b981", font=font_label_bold)
        
        canal_text = f"CANAL: {self.canal.upper()}"
        canal_color = "#38bdf8" if self.canal == "Minorista" else "#a78bfa"
        draw.text((750, 500), canal_text, fill=canal_color, font=font_label_bold)
        
        # --- DIBUJAR PRODUCTO EN LA BANDEJA DE LA BALANZA ---
        if info:
            img_path = info.get("imagen", "")
            if img_path and os.path.exists(img_path):
                try:
                    plate_img = Image.open(img_path).convert("RGBA")
                    # Recortar bordes transparentes
                    bbox = plate_img.getbbox()
                    if bbox:
                        plate_img = plate_img.crop(bbox)
                    # Redimensionar para la bandeja
                    plate_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                    
                    # Centrado X = 600, resting on tray surface Y = 965
                    px = 600 - plate_img.width // 2
                    py = 965 - plate_img.height
                    img.paste(plate_img, (px, py), plate_img)
                except Exception as ex:
                    print(f"Error al dibujar producto en la bandeja: {ex}")
        
        return img

    def actualizar_imagen_balanza(self):
        """
        Genera y actualiza la imagen en el widget.
        """
        pil_img = self.generar_imagen_pantalla()
        self.ctk_img = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(540, 540)
        )
        self.lblBalanza.configure(image=self.ctk_img)

    def crear_componentes(self):
        # Grid para 3 columnas: Catálogo (300px), Controles (340px), Balanza (600px)
        self.ventana.grid_columnconfigure(0, weight=3) # Catálogo
        self.ventana.grid_columnconfigure(1, weight=3) # Controles
        self.ventana.grid_columnconfigure(2, weight=5) # Balanza
        self.ventana.grid_rowconfigure(0, weight=1)
        
        # 1. Crear el Panel del Catálogo (Columna 0)
        self.crear_panel_catalogo()
        
        # 2. Crear el Panel de Control y Ventas (Columna 1)
        self.crear_panel_controles()
        
        # 3. Crear el Panel de la Balanza Visual (Columna 2)
        self.crear_panel_balanza()

    def crear_panel_catalogo(self):
        panel_cat = ctk.CTkFrame(self.ventana, corner_radius=15, fg_color="#1e293b")
        panel_cat.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        
        # Título del catálogo
        ctk.CTkLabel(
            panel_cat,
            text="📦 CATÁLOGO",
            font=("Arial", 20, "bold"),
            text_color="#22d3ee"
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            panel_cat,
            text="Arrastre un producto a la balanza",
            font=("Arial", 12, "italic"),
            text_color="#94a3b8"
        ).pack(pady=(0, 15))
        
        # Frame scrollable para los productos
        scroll_cat = ctk.CTkScrollableFrame(
            panel_cat,
            fg_color="#0f172a",
            corner_radius=10
        )
        scroll_cat.pack(padx=15, pady=(0, 15), fill="both", expand=True)
        
        # Instanciar las tarjetas de productos
        self.tarjetas_img_ref = [] # Referencias para evitar recolección de basura
        
        for prod_name, info in PRODUCTOS_DB.items():
            card = ctk.CTkFrame(scroll_cat, fg_color="#1e293b", corner_radius=8, cursor="hand2")
            card.pack(pady=6, fill="x", padx=4)
            
            # Cargar imagen en miniatura (60x60)
            img_path = info.get("imagen", "")
            img_label = None
            if img_path and os.path.exists(img_path):
                try:
                    pil_raw = Image.open(img_path).convert("RGBA")
                    pil_raw.thumbnail((60, 60), Image.Resampling.LANCZOS)
                    ctk_thumb = ctk.CTkImage(light_image=pil_raw, dark_image=pil_raw, size=(55, 55))
                    self.tarjetas_img_ref.append(ctk_thumb) # Salvar referencia
                    
                    img_label = ctk.CTkLabel(card, image=ctk_thumb, text="")
                    img_label.pack(side="left", padx=8, pady=8)
                except Exception as ex:
                    print(f"Error cargando miniatura de {prod_name}: {ex}")
            
            # Frame interno para textos
            txt_frame = ctk.CTkFrame(card, fg_color="transparent")
            txt_frame.pack(side="left", fill="both", expand=True, padx=5, pady=8)
            
            lbl_name = ctk.CTkLabel(
                txt_frame,
                text=prod_name.upper(),
                font=("Arial", 14, "bold"),
                text_color="#f8fafc",
                anchor="w"
            )
            lbl_name.pack(fill="x")
            
            # Nota: Los precios cambian dinámicamente, pero mostramos los dos de referencia
            precios_str = f"Min: S/.{info['precio_minorista']:.2f}\nMay: S/.{info['precio_mayorista']:.2f}"
            lbl_price = ctk.CTkLabel(
                txt_frame,
                text=precios_str,
                font=("Arial", 11),
                text_color="#fb923c",
                anchor="w",
                justify="left"
            )
            lbl_price.pack(fill="x")
            
            # Configurar Bindings de Drag & Drop
            setup_drag = lambda event, name=prod_name: self.iniciar_arrastre(event, name)
            
            card.bind("<ButtonPress-1>", setup_drag)
            card.bind("<B1-Motion>", self.mover_arrastre)
            card.bind("<ButtonRelease-1>", lambda event, name=prod_name: self.soltar_arrastre(event, name))
            
            # Enlazar a los elementos hijos
            for widget in (img_label, txt_frame, lbl_name, lbl_price):
                if widget:
                    widget.bind("<ButtonPress-1>", setup_drag)
                    widget.bind("<B1-Motion>", self.mover_arrastre)
                    widget.bind("<ButtonRelease-1>", lambda event, name=prod_name: self.soltar_arrastre(event, name))

    def crear_panel_controles(self):
        panel_ctrl = ctk.CTkFrame(self.ventana, corner_radius=15, fg_color="#1e293b")
        panel_ctrl.grid(row=0, column=1, padx=10, pady=20, sticky="nsew")
        
        # Título
        ctk.CTkLabel(
            panel_ctrl,
            text="⚖️ PANEL DE CONTROL",
            font=("Arial", 20, "bold"),
            text_color="#38bdf8"
        ).pack(pady=20)
        
        # Frame de configuraciones
        config_frame = ctk.CTkFrame(panel_ctrl, fg_color="#0f172a", corner_radius=10)
        config_frame.pack(padx=20, pady=10, fill="x")
        
        # Mercado
        ctk.CTkLabel(
            config_frame,
            text="Punto de Venta / Mercado:",
            font=("Arial", 13, "bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=15, pady=(15, 3))
        
        self.comboMercado = ctk.CTkOptionMenu(
            config_frame,
            values=MERCADOS_MINORISTAS,
            font=("Arial", 13),
            dropdown_font=("Arial", 13),
            command=lambda _: self.actualizar_imagen_balanza()
        )
        self.comboMercado.set(MERCADOS_MINORISTAS[0])
        self.comboMercado.pack(padx=15, pady=(0, 15), fill="x")
        
        # Selector de Canal de Venta (Minorista / Mayorista)
        ctk.CTkLabel(
            config_frame,
            text="Canal / Tipo de Venta:",
            font=("Arial", 13, "bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=15, pady=(0, 3))
        
        self.btnCanal = ctk.CTkSegmentedButton(
            config_frame,
            values=["Minorista", "Mayorista"],
            command=self.cambiar_canal,
            font=("Arial", 12, "bold")
        )
        self.btnCanal.pack(padx=15, pady=(0, 15), fill="x")
        self.btnCanal.set("Minorista")
        
        # Producto (invisible pero mantenido para retrocompatibilidad/lógica)
        self.comboProducto = ctk.CTkOptionMenu(
            config_frame,
            values=obtener_productos(),
            command=self.actualizar_producto_seleccionado
        )
        
        # Botones
        botones_frame = ctk.CTkFrame(panel_ctrl, fg_color="transparent")
        botones_frame.pack(padx=20, pady=10, fill="x")
        
        self.btnPesar = ctk.CTkButton(
            botones_frame,
            text="⚖️ SIMULAR PESAR",
            font=("Arial", 14, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=45,
            command=self.pesar
        )
        self.btnPesar.pack(pady=5, fill="x")
        
        self.btnRegistrar = ctk.CTkButton(
            botones_frame,
            text="💾 REGISTRAR VENTA",
            font=("Arial", 14, "bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=40,
            command=self.registrar
        )
        self.btnRegistrar.pack(pady=5, fill="x")
        
        self.btnEnviar = ctk.CTkButton(
            botones_frame,
            text="📡 ENVIAR IoT",
            font=("Arial", 14, "bold"),
            fg_color="#4b5563",
            hover_color="#374151",
            height=40,
            command=self.enviar
        )
        self.btnEnviar.pack(pady=5, fill="x")
        
        # Historial
        ctk.CTkLabel(
            panel_ctrl,
            text="📋 Historial de Ventas Recientes",
            font=("Arial", 14, "bold"),
            text_color="#f8fafc"
        ).pack(pady=(15, 3), anchor="w", padx=25)
        
        self.table_frame = ctk.CTkScrollableFrame(
            panel_ctrl,
            fg_color="#0f172a",
            height=200,
            corner_radius=10
        )
        self.table_frame.pack(padx=20, pady=(0, 5), fill="both", expand=True)
        
        # Botones de exportación Excel / CSV
        export_frame = ctk.CTkFrame(panel_ctrl, fg_color="transparent")
        export_frame.pack(padx=20, pady=(0, 15), fill="x")
        
        self.btnExportExcel = ctk.CTkButton(
            export_frame,
            text="📥 EXCEL",
            font=("Arial", 12, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=32,
            width=100,
            command=self.exportar_excel
        )
        self.btnExportExcel.pack(side="left", expand=True, padx=(0, 5), fill="x")
        
        self.btnExportCSV = ctk.CTkButton(
            export_frame,
            text="📥 CSV",
            font=("Arial", 12, "bold"),
            fg_color="#06b6d4",
            hover_color="#0891b2",
            height=32,
            width=100,
            command=self.exportar_csv
        )
        self.btnExportCSV.pack(side="right", expand=True, padx=(5, 0), fill="x")

    def crear_panel_balanza(self):
        panel_bal = ctk.CTkFrame(self.ventana, corner_radius=15, fg_color="transparent")
        panel_bal.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")
        
        # Etiqueta de la imagen de la balanza
        self.lblBalanza = ctk.CTkLabel(panel_bal, text="")
        self.lblBalanza.pack(expand=True)

    # ---------------------------------
    # DRAG & DROP INTERACTION LOGIC
    # ---------------------------------
    def iniciar_arrastre(self, event, product_name):
        self.arrastrando = True
        self.producto_arrastrado = product_name
        self.actualizar_imagen_balanza()
        
        # Crear ventana flotante
        self.drag_window = ctk.CTkToplevel(self.ventana)
        self.drag_window.overrideredirect(True)
        self.drag_window.attributes("-topmost", True)
        
        try:
            self.drag_window.attributes("-alpha", 0.85)
        except Exception:
            pass
            
        self.drag_window.configure(fg_color="#06b6d4")
        
        info = PRODUCTOS_DB.get(product_name)
        if info:
            img_path = info.get("imagen", "")
            if img_path and os.path.exists(img_path):
                try:
                    pil_thumb = Image.open(img_path).convert("RGBA")
                    pil_thumb.thumbnail((45, 45), Image.Resampling.LANCZOS)
                    ctk_thumb = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=(40, 40))
                    self.drag_window_img_ref = ctk_thumb
                    
                    lbl_img = ctk.CTkLabel(self.drag_window, image=ctk_thumb, text="")
                    lbl_img.pack(side="left", padx=(10, 5), pady=8)
                except Exception:
                    pass
                    
        lbl_txt = ctk.CTkLabel(
            self.drag_window,
            text=product_name.upper(),
            font=("Arial", 12, "bold"),
            text_color="#0f172a"
        )
        lbl_txt.pack(side="left", padx=(5, 12), pady=8)
        self.drag_window.geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

    def mover_arrastre(self, event):
        if self.drag_window:
            self.drag_window.geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

    def soltar_arrastre(self, event, product_name):
        self.arrastrando = False
        
        # Destruir ventana flotante diferidamente
        if self.drag_window:
            win = self.drag_window
            self.drag_window = None
            self.ventana.after(100, win.destroy)
            
        balanza_x = self.lblBalanza.winfo_rootx()
        balanza_y = self.lblBalanza.winfo_rooty()
        balanza_w = self.lblBalanza.winfo_width()
        balanza_h = self.lblBalanza.winfo_height()
        
        cursor_x = event.x_root
        cursor_y = event.y_root
        
        if (balanza_x <= cursor_x <= balanza_x + balanza_w) and (balanza_y <= cursor_y <= balanza_y + balanza_h):
            self.comboProducto.set(product_name)
            self.actualizar_producto_seleccionado(product_name)
            self.pesar()
        else:
            self.actualizar_imagen_balanza()

    # ---------------------------------
    def cambiar_canal(self, canal):
        """
        Cambia el canal seleccionado (Minorista/Mayorista), actualiza los mercados del combobox y recalcula.
        """
        self.canal = canal
        
        # Actualizar dinámicamente los mercados en el combobox según el canal
        if self.canal == "Mayorista":
            self.comboMercado.configure(values=MERCADOS_MAYORISTAS)
            self.comboMercado.set(MERCADOS_MAYORISTAS[0])
        else:
            self.comboMercado.configure(values=MERCADOS_MINORISTAS)
            self.comboMercado.set(MERCADOS_MINORISTAS[0])
            
        producto = self.comboProducto.get()
        self.precio = obtener_precio(producto, self.canal)
        self.total = round(self.peso * self.precio, 2)
        self.actualizar_imagen_balanza()

    def cargar_tabla_ventas(self):
        """
        Lee el archivo ventas.csv y renderiza las últimas 6 ventas con la nueva estructura de 12 columnas.
        """
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        headers = ["Fecha", "Producto", "Mayorista", "Minorista"]
        for col_idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.table_frame,
                text=text,
                font=("Arial", 11, "bold"),
                text_color="#38bdf8"
            )
            lbl.grid(row=0, column=col_idx, padx=6, pady=5, sticky="w")
            
        div = ctk.CTkFrame(self.table_frame, height=2, fg_color="#1e293b")
        div.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        
        try:
            df = obtener_historial()
            if df.empty:
                lbl = ctk.CTkLabel(
                    self.table_frame,
                    text="No hay registros.",
                    font=("Arial", 11, "italic"),
                    text_color="#64748b"
                )
                lbl.grid(row=2, column=0, columnspan=4, pady=15)
                return
                
            ventas_recientes = df.tail(6).iloc[::-1]
            
            for row_idx, (_, row) in enumerate(ventas_recientes.iterrows(), start=2):
                fecha_completa = str(row.get("Fecha", ""))
                try:
                    dt = datetime.strptime(fecha_completa, "%d/%m/%Y %H:%M:%S")
                    fecha_corta = dt.strftime("%d/%m %H:%M")
                except Exception:
                    fecha_corta = fecha_completa[:11]
                    
                prod = str(row.get("Productos", "N/A"))
                p_may = f"S/. {float(row.get('Mayorista - Precio Prom.', 0.0)):.2f}"
                p_min = f"S/. {float(row.get('Minorista - Precio Prom.', 0.0)):.2f}"
                
                ctk.CTkLabel(self.table_frame, text=fecha_corta, font=("Arial", 11), text_color="#94a3b8").grid(row=row_idx, column=0, padx=6, pady=3, sticky="w")
                ctk.CTkLabel(self.table_frame, text=prod, font=("Arial", 11, "bold"), text_color="#f8fafc").grid(row=row_idx, column=1, padx=6, pady=3, sticky="w")
                ctk.CTkLabel(self.table_frame, text=p_may, font=("Arial", 11), text_color="#a78bfa").grid(row=row_idx, column=2, padx=6, pady=3, sticky="w")
                ctk.CTkLabel(self.table_frame, text=p_min, font=("Arial", 11), text_color="#06b6d4").grid(row=row_idx, column=3, padx=6, pady=3, sticky="w")
                
        except Exception as e:
            print(f"Error al cargar tabla de ventas: {e}")
            lbl = ctk.CTkLabel(
                self.table_frame,
                text="Error al leer historial.",
                font=("Arial", 11, "italic"),
                text_color="#ef4444"
            )
            lbl.grid(row=2, column=0, columnspan=4, pady=15)

    def actualizar_producto_seleccionado(self, producto):
        self.precio = obtener_precio(producto, self.canal)
        self.peso = 0.0
        self.total = 0.0
        self.actualizar_imagen_balanza()

    def actualizar_peso(self, peso):
        self.peso = peso
        self.total = round(self.peso * self.precio, 2)
        self.actualizar_imagen_balanza()
        self.ventana.update()

    def pesar(self):
        self.btnPesar.configure(state="disabled")
        self.btnRegistrar.configure(state="disabled")
        
        self.peso = self.balanza.animacion(self.actualizar_peso)
        self.total = self.balanza.calcular_total(self.precio)
        self.actualizar_imagen_balanza()
        
        self.btnPesar.configure(state="normal")
        self.btnRegistrar.configure(state="normal")

    def registrar(self):
        if self.peso <= 0:
            messagebox.showwarning("Atención", "Por favor, realice el pesaje del producto primero.")
            return
            
        registrar_venta(
            self.comboMercado.get(),
            self.canal,
            self.comboProducto.get(),
            self.peso,
            self.precio,
            self.total
        )
        
        self.cargar_tabla_ventas()
        
        self.peso = 0.0
        self.total = 0.0
        self.actualizar_imagen_balanza()
        
        messagebox.showinfo("Correcto", f"Venta de {self.comboProducto.get()} ({self.canal}) registrada exitosamente.")

    def enviar(self):
        from tkinter import simpledialog, messagebox
        import json
        
        CONFIG_FILE = "config.json"
        saved_pass = ""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved_pass = json.load(f).get("db_password", "")
            except Exception:
                pass
                
        password = simpledialog.askstring(
            "Conexión Supabase IoT", 
            "Ingrese su contraseña de Supabase:", 
            show='*', 
            initialvalue=saved_pass
        )
        if password is not None:
            # Guardar contraseña para comodidad
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"db_password": password}, f)
            except Exception:
                pass
                
            db_url = f"postgresql://postgres.ivimhckgfcerbdfjohlf:{password}@aws-1-us-west-2.pooler.supabase.com:6543/postgres"
            
            # Cambiar cursor a cargando
            self.ventana.config(cursor="watch")
            self.ventana.update()
            
            success, msg = enviar_datos_supabase(db_url)
            
            # Restaurar cursor normal
            self.ventana.config(cursor="")
            
            if success:
                messagebox.showinfo("Correcto", msg)
            else:
                messagebox.showerror("Error", msg)

    def exportar_excel(self):
        from tkinter import filedialog, messagebox
        import pandas as pd
        
        try:
            df = obtener_historial()
            if df.empty:
                messagebox.showwarning("Atención", "No hay datos en el historial para exportar.")
                return
                
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Archivos de Excel", "*.xlsx")],
                title="Guardar como Excel"
            )
            if path:
                df.to_excel(path, index=False)
                messagebox.showinfo("Éxito", f"Historial exportado correctamente a:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar a Excel: {e}")

    def exportar_csv(self):
        from tkinter import filedialog, messagebox
        import shutil
        
        try:
            df = obtener_historial()
            if df.empty:
                messagebox.showwarning("Atención", "No hay datos en el historial para exportar.")
                return
                
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("Archivos CSV", "*.csv")],
                title="Guardar como CSV"
            )
            if path:
                shutil.copy2(ARCHIVO, path)
                messagebox.showinfo("Éxito", f"Historial exportado correctamente a:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar a CSV: {e}")