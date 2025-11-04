"""
Configuración de posiciones de texto en la plantilla de ofertas
"""
import json
import os

# Posiciones basadas en plantilla de 1080x1350 píxeles
# Basado en el ejemplo correcto de Naranja proporcionado por el usuario
DEFAULT_POSITIONS = {
    "title": {
        "x": "center",
        "y": 290,  # Justo debajo de la línea horizontal
        "font_size": 48,
        "bold": True
    },
    "product_name": {
        "x": "center",
        "y": 360,  # Debajo del título
        "font_size": 44,
        "bold": False
    },
    "price": {
        "x": "center",
        "y": 415,  # Justo después del nombre del producto
        "font_size": 46,
        "bold": True
    },
    "product_image": {
        "x": "center",
        "y": 750,  # Centro de la imagen (mucho más grande)
        "max_width": 0.75,  # 75% del ancho de la plantilla
        "max_height": 0.45  # 45% de la altura - imagen más grande
    },
    "reference_price": {
        "x": "center",
        "y": 1040,  # Abajo, antes del contacto de WhatsApp
        "font_size": 26,
        "bold": False,
        "italic": True
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

