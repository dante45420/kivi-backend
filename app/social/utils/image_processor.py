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
        print(f"  Intentando descargar imagen de: {url}")
        
        # Headers para simular un navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        print(f"  ✓ Respuesta HTTP: {response.status_code}")
        print(f"  ✓ Tamaño: {len(response.content)} bytes")
        
        img = Image.open(BytesIO(response.content))
        print(f"  ✓ Imagen cargada: {img.format} {img.size} {img.mode}")
        
        return img.convert('RGBA')
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error de red descargando imagen: {e}")
        print(f"     URL: {url}")
        return None
    except Exception as e:
        print(f"  ❌ Error procesando imagen: {e}")
        print(f"     URL: {url}")
        return None


def get_font(size: int, bold: bool = False, italic: bool = False) -> Optional[ImageFont.FreeTypeFont]:
    """Obtiene una fuente del sistema"""
    try:
        # Intentar usar fuentes del sistema
        if bold and italic:
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf',
            ]
        elif bold:
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
        elif italic:
            font_paths = [
                '/System/Library/Fonts/Supplemental/Arial Italic.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf',
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
    except Exception as e:
        print(f"Warning: No se pudo cargar la fuente, usando default: {e}")
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
        ref_price_font = get_font(
            positions['reference_price']['font_size'], 
            bold=positions['reference_price'].get('bold', False),
            italic=positions['reference_price'].get('italic', False)
        )
        
        # Colores corregidos según feedback
        # Verde del logo Kivi: RGB(76, 175, 80) aproximadamente
        kivi_green = (76, 175, 80)  # Verde brillante del logo Kivi
        black_color = (0, 0, 0)  # Negro para nombre y precio
        gray_color = (80, 80, 80)  # Gris más oscuro para precio referencia
        
        # Obtener posiciones en píxeles directamente
        title_y = int(positions['title']['y'])
        product_y = int(positions['product_name']['y'])
        price_y = int(positions['price']['y'])
        product_image_y = int(positions['product_image']['y'])
        ref_price_y = int(positions['reference_price']['y'])
        
        # Función para centrar texto
        def center_text(text, font, y_position, color):
            """Dibuja texto centrado"""
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x_position = (width - text_width) // 2
            draw.text((x_position, y_position), text, fill=color, font=font)
            print(f"  Dibujando '{text}' en posición ({x_position}, {y_position})")
        
        # Dibujar título con verde Kivi (arriba de la línea separadora)
        print(f"Dibujando título: {title}")
        center_text(title, title_font, title_y, kivi_green)
        
        # Dibujar nombre del producto en NEGRO (abajo de la línea separadora)
        product_text = f"{product_name}:"
        print(f"Dibujando nombre producto: {product_text}")
        center_text(product_text, product_font, product_y, black_color)
        
        # Dibujar precio en NEGRO NEGRITA DESTACADO
        print(f"Dibujando precio: {price}")
        center_text(price, price_font, price_y, black_color)
        
        # Descargar y colocar imagen del producto
        print(f"Descargando imagen del producto desde: {product_image_url}")
        product_img = download_image(product_image_url)
        if product_img:
            print(f"✓ Imagen descargada exitosamente: {product_img.size}")
            
            # Redimensionar imagen del producto - hacerla grande como en el ejemplo
            max_img_width = int(width * positions['product_image']['max_width'])
            max_img_height = int(height * positions['product_image']['max_height'])
            print(f"  Tamaño máximo permitido: {max_img_width}x{max_img_height}")
            
            # Calcular proporciones manteniendo aspect ratio
            img_ratio = product_img.width / product_img.height
            target_ratio = max_img_width / max_img_height
            
            if img_ratio > target_ratio:
                # La imagen es más ancha que el target
                new_width = max_img_width
                new_height = int(max_img_width / img_ratio)
            else:
                # La imagen es más alta que el target
                new_height = max_img_height
                new_width = int(max_img_height * img_ratio)
            
            print(f"  Redimensionando a: {new_width}x{new_height}")
            product_img = product_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Centrar la imagen horizontalmente y posicionarla verticalmente
            img_x = (width - new_width) // 2
            # product_image_y es el centro de donde queremos la imagen, ajustar para que sea la esquina superior
            img_y = product_image_y - (new_height // 2)
            print(f"  Posicionando imagen en: ({img_x}, {img_y})")
            
            # Pegar imagen sobre la plantilla
            # Si la imagen tiene transparencia, usarla como máscara
            if product_img.mode == 'RGBA':
                img.paste(product_img, (img_x, img_y), product_img)
            else:
                # Convertir a RGBA y pegar
                product_img = product_img.convert('RGBA')
                img.paste(product_img, (img_x, img_y), product_img)
            
            print("✓ Imagen del producto pegada exitosamente")
        else:
            print(f"❌ ERROR: No se pudo descargar la imagen del producto desde: {product_image_url}")
            print(f"   La imagen NO se incluirá en el resultado final")
            # No retornar None - continuar con el resto de la generación
        
        # Dibujar precio de referencia en cursiva y gris
        if reference_price:
            ref_text = f"(Precio referencia: {reference_price})"
            print(f"Dibujando precio de referencia: {ref_text}")
            center_text(ref_text, ref_price_font, ref_price_y, gray_color)
        
        # Guardar imagen
        if not output_path:
            # Crear directorio de imágenes generadas en la raíz del backend
            # Desde: backend/app/social/utils/image_processor.py
            # Hacia: backend/generated_images
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            # current_file_dir = backend/app/social/utils
            # Necesitamos ir a backend/generated_images
            backend_root = os.path.join(current_file_dir, '..', '..', '..')
            backend_root = os.path.abspath(backend_root)
            output_dir = os.path.join(backend_root, 'generated_images')
            os.makedirs(output_dir, exist_ok=True)
            
            # Nombre de archivo único basado en tipo y nombre del producto
            safe_product_name = product_name.replace(' ', '_').replace('/', '_').lower()
            filename = f"oferta_{offer_type}_{safe_product_name}.png"
            output_path = os.path.join(output_dir, filename)
        
        # Convertir a RGB para guardar como PNG
        final_img = Image.new('RGB', img.size, (255, 255, 255))
        final_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        final_img.save(output_path, 'PNG', quality=95)
        
        print(f"✅ Imagen generada y guardada en: {output_path}")
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

