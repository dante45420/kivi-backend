"""
Configuración de posiciones de texto en la plantilla de ofertas
"""
import json
import os

# Posiciones basadas en plantilla de 1080x1350 píxeles
# Nombre y precio en la MISMA línea, precio ref MUCHO más grande
DEFAULT_POSITIONS = {
    "title": {
        "x": "center",
        "y": 380,  # Más cerca de la línea separadora (~420px)
        "font_size": 50,
        "bold": True,
        "font_style": "rounded"  # Fuente más redonda
    },
    "product_name": {
        "x": "left",  # Ahora se posiciona dinámicamente al lado del precio
        "y": 490,  # MISMA altura que el precio
        "font_size": 42,
        "bold": False,
        "color": "black"
    },
    "price": {
        "x": "right",  # Ahora se posiciona dinámicamente al lado del nombre
        "y": 490,  # MISMA altura que el nombre
        "font_size": 54,
        "bold": True,
        "color": "black"  # Precio en negro NEGRITA destacado
    },
    "product_image": {
        "x": "center",
        "y": 820,  # Centro de la imagen
        "max_width": 0.70,  # 70% del ancho de la plantilla
        "max_height": 0.38  # 38% de la altura
    },
    "reference_price": {
        "x": "center",
        "y": 1060,  # Antes del contacto de WhatsApp
        "font_size": 38,  # MUCHO más grande (era 30)
        "bold": False,
        "italic": True,
        "color": "gray"
    }
}

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    'social_image_positions.json'
)


def get_positions():
    """Obtiene las posiciones configuradas, o las por defecto si no existe configuración"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando posiciones: {e}")
    
    return DEFAULT_POSITIONS.copy()


def save_positions(positions):
    """Guarda las posiciones en el archivo de configuración"""
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(positions, f, indent=2)
        return True
    except Exception as e:
        print(f"Error guardando posiciones: {e}")
        return False


def update_positions(updates):
    """Actualiza las posiciones con los valores proporcionados"""
    positions = get_positions()
    positions.update(updates)
    return save_positions(positions)

