# ==========================================
# productos.py
# Catálogo de productos e información de precios, imágenes y unidades
# ==========================================

MERCADOS = [
    "Mercado Central",
    "Mercado Mayorista",
    "Mercado San José",
    "Supermercado Metro"
]

PRODUCTOS_DB = {
    "Papa": {
        "codigo": "P-001",
        "categoria": "Tubérculos",
        "precio_minorista": 2.50,
        "precio_mayorista": 1.60,
        "unidad_mayorista": "Saco",
        "equiv_mayorista": 50.0,
        "imagen": "productos/papa.png"
    },
    "Tomate": {
        "codigo": "P-002",
        "categoria": "Verduras",
        "precio_minorista": 4.50,
        "precio_mayorista": 2.80,
        "unidad_mayorista": "Cajón",
        "equiv_mayorista": 20.0,
        "imagen": "productos/tomate.png"
    },
    "Cebolla": {
        "codigo": "P-003",
        "categoria": "Verduras",
        "precio_minorista": 3.00,
        "precio_mayorista": 1.80,
        "unidad_mayorista": "Saco",
        "equiv_mayorista": 45.0,
        "imagen": "productos/cebolla.png"
    },
    "Zanahoria": {
        "codigo": "P-004",
        "categoria": "Verduras",
        "precio_minorista": 3.80,
        "precio_mayorista": 2.20,
        "unidad_mayorista": "Saco",
        "equiv_mayorista": 50.0,
        "imagen": "productos/zanahoria.png"
    },
    "Choclo": {
        "codigo": "P-005",
        "categoria": "Cereales",
        "precio_minorista": 5.00,
        "precio_mayorista": 3.20,
        "unidad_mayorista": "Ciento",
        "equiv_mayorista": 40.0,
        "imagen": "productos/choclo.png"
    }
}

def obtener_productos():
    """
    Retorna la lista de nombres de los productos disponibles.
    """
    return list(PRODUCTOS_DB.keys())

def obtener_precio(producto, canal="Minorista"):
    """
    Retorna el precio por kg del producto según el canal (Minorista/Mayorista).
    Si no existe, retorna 0.0.
    """
    info = PRODUCTOS_DB.get(producto)
    if not info:
        return 0.0
    
    if canal == "Mayorista":
        return info.get("precio_mayorista", 0.0)
    else:
        return info.get("precio_minorista", 0.0)

def obtener_info_producto(producto):
    """
    Retorna toda la metadata asociada al producto.
    """
    return PRODUCTOS_DB.get(producto)