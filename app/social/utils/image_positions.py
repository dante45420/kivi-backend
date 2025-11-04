"""
Configuración de posiciones de texto en la plantilla de ofertas
"""
import json
import os

DEFAULT_POSITIONS = {
    "title": {
        "x": "center",  # "center" o número en píxeles
        "y": 0.25,  # Porcentaje de altura (0.0 a 1.0)
        "font_size": 60,
        "bold": True
    },
    "product_name": {
        "x": "center",
        "y": 0.35,
        "font_size": 50,
        "bold": True
    },
    "price": {
        "x": "center",
        "y": 0.45,
        "font_size": 45,
        "bold": True
    },
    "product_image": {
        "x": "center",
        "y": 0.50,
        "max_width": 0.6,  # Porcentaje del ancho
        "max_height": 0.3  # Porcentaje de la altura
    },
    "reference_price": {
        "x": "center",
        "y": 0.80,
        "font_size": 35,
        "bold": False
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

