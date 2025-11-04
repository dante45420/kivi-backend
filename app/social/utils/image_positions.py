"""
Configuración de posiciones de texto en la plantilla de ofertas
"""
import json
import os

# Posiciones basadas en plantilla de 1080x1350 píxeles
# Basado en los ejemplos proporcionados por el usuario
DEFAULT_POSITIONS = {
    "title": {
        "x": "center",
        "y": 0.20,  # Aproximadamente 270px desde arriba (después del logo)
        "font_size": 50,
        "bold": True
    },
    "product_name": {
        "x": "center",
        "y": 0.28,  # Aproximadamente 378px desde arriba
        "font_size": 42,
        "bold": True
    },
    "price": {
        "x": "center",
        "y": 0.32,  # Aproximadamente 432px desde arriba (justo después del nombre)
        "font_size": 40,
        "bold": True
    },
    "product_image": {
        "x": "center",
        "y": 0.40,  # Aproximadamente 540px desde arriba (centro de la imagen)
        "max_width": 0.65,  # 65% del ancho de la plantilla
        "max_height": 0.35  # 35% de la altura de la plantilla
    },
    "reference_price": {
        "x": "center",
        "y": 0.75,  # Aproximadamente 1012px desde arriba (abajo, antes del contacto)
        "font_size": 28,
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

