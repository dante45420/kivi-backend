"""
Procesador de imágenes para generar ofertas semanales usando plantilla
"""
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple
from .image_positions import get_positions


def get_template_path() -> str:
    """Obtiene la ruta de la plantilla"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, '..', 'templates', 'plantilla_oferta_semana.png')


def download_image(url: str) -> Optional[Image.Image]:
    """Descarga una imagen desde una URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img.convert('RGBA')
    except Exception as e:
        print(f"Error descargando imagen desde {url}: {e}")
        return None


def get_font(size: int, bold: bool = False) -> Optional[ImageFont.FreeTypeFont]:
    """Obtiene una fuente del sistema"""
    try:
        # Intentar usar fuentes del sistema
        if bold:
            # Intentar fuentes bold comunes
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
        else:
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        
        # Si no encuentra fuente, usar la por defecto
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def generate_offer_image(
    offer_type: str,  # 'fruta', 'verdura', 'especial'
    product_name: str,
    price: str,
    reference_price: str,
    product_image_url: str,
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Genera una imagen de oferta usando la plantilla
    
    Args:
        offer_type: Tipo de oferta ('fruta', 'verdura', 'especial')
        product_name: Nombre del producto
        price: Precio de la oferta (ej: "$1.500 kg")
        reference_price: Precio de referencia (ej: "Jumbo $2.500 kg")
        product_image_url: URL de la imagen del producto
        output_path: Ruta donde guardar la imagen (opcional)
    
    Returns:
        Ruta de la imagen generada o None si hay error
    """
    try:
        # Cargar plantilla
        template_path = get_template_path()
        if not os.path.exists(template_path):
            print(f"Plantilla no encontrada en: {template_path}")
            return None
        
        template = Image.open(template_path).convert('RGBA')
        width, height = template.size
        
        # Crear una copia para trabajar
        img = template.copy()
        draw = ImageDraw.Draw(img)
        
        # Obtener posiciones configuradas
        positions = get_positions()
        
        # Determinar título según el tipo
        type_titles = {
            'fruta': '¡Fruta de la semana!',
            'verdura': '¡Verdura de la semana!',
            'especial': '¡Fruta Especial de la semana!'
        }
        title = type_titles.get(offer_type, '¡Oferta de la semana!')
        
        # Configurar fuentes usando las posiciones configuradas
        title_font = get_font(positions['title']['font_size'], bold=positions['title']['bold'])
        product_font = get_font(positions['product_name']['font_size'], bold=positions['product_name']['bold'])
        price_font = get_font(positions['price']['font_size'], bold=positions['price']['bold'])
        ref_price_font = get_font(positions['reference_price']['font_size'], bold=positions['reference_price']['bold'])
        
        # Colores (ajustar según la plantilla)
        text_color = (34, 34, 34)  # Dark grey/black
        dark_green = (34, 139, 34)  # Dark green
        
        # Calcular posiciones usando la configuración
        def calculate_x(pos_config, text_width):
            """Calcula la posición X"""
            if pos_config['x'] == 'center':
                return (width - text_width) // 2
            elif isinstance(pos_config['x'], (int, float)):
                return int(pos_config['x'])
            else:
                return (width - text_width) // 2  # Fallback a center
        
        def calculate_y(pos_config):
            """Calcula la posición Y"""
            if isinstance(pos_config['y'], (int, float)):
                if 0 <= pos_config['y'] <= 1:
                    # Es un porcentaje
                    return int(height * pos_config['y'])
                else:
                    # Es un valor en píxeles
                    return int(pos_config['y'])
            return int(height * 0.5)  # Fallback
        
        title_y = calculate_y(positions['title'])
        product_y = calculate_y(positions['product_name'])
        price_y = calculate_y(positions['price'])
        product_image_y = calculate_y(positions['product_image'])
        ref_price_y = calculate_y(positions['reference_price'])
        
        # Dibujar título
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = calculate_x(positions['title'], title_width)
        draw.text((title_x, title_y), title, fill=dark_green, font=title_font)
        
        # Dibujar nombre del producto
        product_text = f"{product_name}:"
        product_bbox = draw.textbbox((0, 0), product_text, font=product_font)
        product_width = product_bbox[2] - product_bbox[0]
        product_x = calculate_x(positions['product_name'], product_width)
        draw.text((product_x, product_y), product_text, fill=text_color, font=product_font)
        
        # Dibujar precio
        price_text = price
        price_bbox = draw.textbbox((0, 0), price_text, font=price_font)
        price_width = price_bbox[2] - price_bbox[0]
        price_x = calculate_x(positions['price'], price_width)
        draw.text((price_x, price_y), price_text, fill=text_color, font=price_font)
        
        # Descargar y colocar imagen del producto
        product_img = download_image(product_image_url)
        if product_img:
            # Redimensionar imagen del producto usando configuración
            max_img_width = int(width * positions['product_image']['max_width'])
            max_img_height = int(height * positions['product_image']['max_height'])
            
            # Calcular proporciones manteniendo aspect ratio
            img_ratio = product_img.width / product_img.height
            target_ratio = max_img_width / max_img_height
            
            if img_ratio > target_ratio:
                new_width = max_img_width
                new_height = int(max_img_width / img_ratio)
            else:
                new_height = max_img_height
                new_width = int(max_img_height * img_ratio)
            
            product_img = product_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Posicionar imagen usando configuración
            img_x = calculate_x(positions['product_image'], new_width)
            img_y = int(product_image_y)
            
            # Pegar imagen sobre la plantilla
            img.paste(product_img, (img_x, img_y), product_img)
        
        # Dibujar precio de referencia
        if reference_price:
            ref_text = f"(Precio referencia: {reference_price})"
            ref_bbox = draw.textbbox((0, 0), ref_text, font=ref_price_font)
            ref_width = ref_bbox[2] - ref_bbox[0]
            ref_x = calculate_x(positions['reference_price'], ref_width)
            draw.text((ref_x, ref_price_y), ref_text, fill=text_color, font=ref_price_font)
        
        # Guardar imagen
        if not output_path:
            # Crear directorio temporal si no existe
            output_dir = os.path.join(os.path.dirname(template_path), '..', '..', '..', 'generated_images')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"oferta_{offer_type}_{product_name.replace(' ', '_').lower()}.png"
            )
        
        # Convertir a RGB para guardar como PNG
        final_img = Image.new('RGB', img.size, (255, 255, 255))
        final_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        final_img.save(output_path, 'PNG', quality=95)
        
        return output_path
        
    except Exception as e:
        print(f"Error generando imagen de oferta: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_offer_image_to_url(
    offer_type: str,
    product_name: str,
    price: str,
    reference_price: str,
    product_image_url: str
) -> Optional[str]:
    """
    Genera una imagen de oferta y retorna la ruta (para uso con URLs públicas)
    Similar a generate_offer_image pero pensado para generar y luego subir a un servicio
    """
    return generate_offer_image(
        offer_type=offer_type,
        product_name=product_name,
        price=price,
        reference_price=reference_price,
        product_image_url=product_image_url
    )

