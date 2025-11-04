"""
Procesador de imágenes para generar ofertas semanales usando plantilla
"""
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple


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
        
        # Determinar título según el tipo
        type_titles = {
            'fruta': '¡Fruta de la semana!',
            'verdura': '¡Verdura de la semana!',
            'especial': '¡Fruta Especial de la semana!'
        }
        title = type_titles.get(offer_type, '¡Oferta de la semana!')
        
        # Configurar fuentes (ajustar tamaños según la plantilla)
        # Estos valores son aproximados y deberían ajustarse según la plantilla real
        title_font = get_font(60, bold=True)
        product_font = get_font(50, bold=True)
        price_font = get_font(45, bold=True)
        ref_price_font = get_font(35, bold=False)
        
        # Colores (ajustar según la plantilla)
        text_color = (34, 34, 34)  # Dark grey/black
        dark_green = (34, 139, 34)  # Dark green
        
        # Posiciones aproximadas (deben ajustarse según la plantilla real)
        # Basado en las descripciones de las imágenes
        title_y = height * 0.25  # Aproximadamente 25% desde arriba
        product_y = height * 0.35
        price_y = height * 0.45
        product_image_y = height * 0.50  # Donde va la imagen del producto
        ref_price_y = height * 0.80
        
        # Dibujar título
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, title_y), title, fill=dark_green, font=title_font)
        
        # Dibujar nombre del producto
        product_text = f"{product_name}:"
        product_bbox = draw.textbbox((0, 0), product_text, font=product_font)
        product_width = product_bbox[2] - product_bbox[0]
        product_x = (width - product_width) // 2
        draw.text((product_x, product_y), product_text, fill=text_color, font=product_font)
        
        # Dibujar precio
        price_text = price
        price_bbox = draw.textbbox((0, 0), price_text, font=price_font)
        price_width = price_bbox[2] - price_bbox[0]
        price_x = (width - price_width) // 2
        draw.text((price_x, price_y), price_text, fill=text_color, font=price_font)
        
        # Descargar y colocar imagen del producto
        product_img = download_image(product_image_url)
        if product_img:
            # Redimensionar imagen del producto (ajustar según la plantilla)
            # La imagen debe caber en el área central
            max_img_width = int(width * 0.6)
            max_img_height = int(height * 0.3)
            
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
            
            # Posicionar imagen en el centro
            img_x = (width - new_width) // 2
            img_y = int(product_image_y)
            
            # Pegar imagen sobre la plantilla
            img.paste(product_img, (img_x, img_y), product_img)
        
        # Dibujar precio de referencia
        if reference_price:
            ref_text = f"(Precio referencia: {reference_price})"
            ref_bbox = draw.textbbox((0, 0), ref_text, font=ref_price_font)
            ref_width = ref_bbox[2] - ref_bbox[0]
            ref_x = (width - ref_width) // 2
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

