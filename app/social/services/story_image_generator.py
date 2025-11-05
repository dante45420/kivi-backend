"""
Generador de imágenes para historias de Instagram
Crea imágenes 1080x1920px con variaciones de diseño
"""
import os
import io
import base64
import re
from typing import Dict, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

# Colores Kivi
KIVI_GREEN_DARK = (60, 121, 76)  # #3C794C
KIVI_ORANGE = (255, 167, 38)  # #FFA726
KIVI_BEIGE = (255, 249, 240)  # #FFF9F0
KIVI_GREEN_LIGHT = (168, 213, 186)  # #A8D5BA
KIVI_TEXT_DARK = (44, 44, 44)  # #2C2C2C
KIVI_GRAY = (128, 128, 128)
KIVI_RED_LIGHT = (255, 200, 200)
KIVI_GREEN_LIGHT_BG = (200, 255, 200)

# Dimensiones de historia de Instagram
STORY_WIDTH = 1080
STORY_HEIGHT = 1920

# Rutas
ASSETS_DIR = os.path.join(os.path.dirname(__file__), '../assets')
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'generated_images', 'stories')
PERRO_FRUTERO_PATH = os.path.join(ASSETS_DIR, 'perro_frutero_kivi.png')

# Asegurar que el directorio de generadas existe
os.makedirs(GENERATED_DIR, exist_ok=True)


class StoryImageGenerator:
    """Genera imágenes de historias con múltiples variaciones de diseño"""
    
    def __init__(self):
        self.story_width = STORY_WIDTH
        self.story_height = STORY_HEIGHT
    
    def generate_story_image(
        self,
        theme: str,
        content_data: dict,
        product_image_url: Optional[str] = None,
        layout_variant: str = 'A'
    ) -> str:
        """
        Genera una imagen de historia
        
        Args:
            theme: Tema de la historia ('tip_semana', 'doggo_prueba', etc)
            content_data: Datos del contenido
            product_image_url: URL de la imagen del producto (opcional)
            layout_variant: Variante de layout ('A', 'B', 'C')
        
        Returns:
            Ruta del archivo generado
        """
        
        generators = {
            'tip_semana': self._generate_tip_semana,
            'doggo_prueba': self._generate_doggo_prueba,
            'mito_realidad': self._generate_mito_realidad,
            'beneficio_dia': self._generate_beneficio_dia,
            'sabias_que': self._generate_sabias_que,
            'detras_camaras': self._generate_detras_camaras,
            'cliente_semana': self._generate_cliente_semana,
            'desafio_receta': self._generate_desafio_receta,
        }
        
        generator_func = generators.get(theme)
        if not generator_func:
            raise ValueError(f"Tema no soportado: {theme}")
        
        return generator_func(content_data, product_image_url, layout_variant)
    
    # ========== GENERADORES POR TEMÁTICA ==========
    
    def _generate_tip_semana(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen para Tip de la Semana"""
        
        # Crear imagen base con fondo beige
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        # Fuentes
        font_title = self._get_font(size=80, bold=True)
        font_subtitle = self._get_font(size=50, bold=False)
        font_body = self._get_font(size=40, bold=False)
        
        # Logo Kivi arriba
        self._draw_logo(img, position='top')
        
        # LAYOUT A: Tip arriba, producto abajo
        if layout == 'A':
            # Título
            self._draw_centered_text(draw, "TIP DE LA SEMANA", 200, font_title, KIVI_GREEN_DARK)
            
            # Icono de bombilla
            self._draw_emoji(img, "💡", (540, 320), size=100)
            
            # Subtítulo
            title = content_data.get('title', 'Título del tip')
            self._draw_centered_multiline(draw, title, 450, 800, font_subtitle, KIVI_TEXT_DARK)
            
            # Steps
            steps = content_data.get('steps', [])
            y_pos = 850
            for i, step in enumerate(steps[:3], 1):
                text = f"{i}. {step}"
                self._draw_wrapped_text(draw, text, 100, y_pos, 880, font_body, KIVI_TEXT_DARK)
                y_pos += 120
            
            # Producto abajo
            if product_image_url:
                self._draw_product_image(img, product_image_url, (540, 1500), max_size=400)
        
        # LAYOUT B: Producto arriba, tip abajo
        elif layout == 'B':
            # Producto arriba
            if product_image_url:
                self._draw_product_image(img, product_image_url, (540, 400), max_size=500)
            
            # Título con fondo
            self._draw_banner(img, 700, KIVI_GREEN_DARK)
            self._draw_centered_text(draw, "TIP DE LA SEMANA", 700, font_title, (255, 255, 255))
            
            # Contenido
            title = content_data.get('title', '')
            self._draw_centered_multiline(draw, title, 900, 800, font_subtitle, KIVI_TEXT_DARK)
            
            steps = content_data.get('steps', [])
            y_pos = 1050
            for step in steps[:3]:
                self._draw_emoji(img, "✓", (120, y_pos), size=50)
                self._draw_wrapped_text(draw, step, 200, y_pos, 700, font_body, KIVI_TEXT_DARK)
                y_pos += 120
        
        # LAYOUT C: Producto en círculo, tip al lado
        else:  # layout == 'C'
            # Título arriba
            self._draw_centered_text(draw, "TIP DE LA SEMANA", 200, font_title, KIVI_GREEN_DARK)
            
            if product_image_url:
                # Producto en círculo a la izquierda
                self._draw_circular_product(img, product_image_url, (270, 600), radius=200)
            
            # Texto a la derecha
            title = content_data.get('title', '')
            steps = content_data.get('steps', [])
            
            y_pos = 450
            for step in steps[:3]:
                self._draw_wrapped_text(draw, f"• {step}", 550, y_pos, 450, font_body, KIVI_TEXT_DARK)
                y_pos += 130
        
        # Pro tip al final
        pro_tip = content_data.get('pro_tip', '')
        if pro_tip:
            self._draw_highlighted_box(img, pro_tip, 1700, KIVI_ORANGE)
        
        # Guardar
        filename = f"story_tip_{content_data.get('product_name', 'general')}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_doggo_prueba(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen del perro probando frutas"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=70, bold=True)
        font_comment = self._get_font(size=45, bold=False)
        font_rating = self._get_font(size=100, bold=True)
        
        # Logo
        self._draw_logo(img, position='top')
        
        # LAYOUT A: Perro arriba, producto abajo
        if layout == 'A':
            # Imagen del perro
            if os.path.exists(PERRO_FRUTERO_PATH):
                self._draw_centered_image(img, PERRO_FRUTERO_PATH, (540, 450), max_size=600)
            
            # Bocadillo de diálogo
            comment = content_data.get('text', '¡Me encanta!')
            self._draw_speech_bubble(img, comment, (540, 800), font_comment)
            
            # Emoji grande
            emoji = content_data.get('emoji', '😍')
            self._draw_emoji(img, emoji, (540, 1050), size=150)
            
            # Producto abajo
            if product_image_url:
                self._draw_product_image(img, product_image_url, (540, 1450), max_size=350)
            
            # Rating
            rating = content_data.get('rating', 10)
            self._draw_centered_text(draw, f"{rating}/10", 1750, font_rating, KIVI_GREEN_DARK)
        
        # LAYOUT B: Split screen
        elif layout == 'B':
            # Línea divisoria vertical
            draw.line([(540, 200), (540, 1750)], fill=KIVI_GREEN_DARK, width=5)
            
            # Perro a la izquierda
            if os.path.exists(PERRO_FRUTERO_PATH):
                self._draw_centered_image(img, PERRO_FRUTERO_PATH, (270, 800), max_size=450)
            
            # Producto a la derecha
            if product_image_url:
                self._draw_product_image(img, product_image_url, (810, 800), max_size=450)
            
            # Texto arriba
            product_name = content_data.get('product_name', 'Fruta')
            self._draw_centered_text(draw, f"DOGGO PRUEBA:\n{product_name.upper()}", 300, font_title, KIVI_GREEN_DARK)
            
            # Reacción abajo
            emoji = content_data.get('emoji', '😍')
            text = content_data.get('text', '¡Delicioso!')
            self._draw_emoji(img, emoji, (540, 1500), size=120)
            self._draw_centered_multiline(draw, text, 1650, 200, font_comment, KIVI_TEXT_DARK)
        
        # LAYOUT C: Perro en círculo
        else:  # layout == 'C'
            # Título
            self._draw_centered_text(draw, "EL CHEF OPINA", 200, font_title, KIVI_GREEN_DARK)
            
            # Perro en círculo grande
            if os.path.exists(PERRO_FRUTERO_PATH):
                self._draw_circular_product(img, PERRO_FRUTERO_PATH, (540, 600), radius=300)
            
            # Producto abajo del perro
            if product_image_url:
                self._draw_product_image(img, product_image_url, (540, 1100), max_size=300)
            
            # Opinión
            text = content_data.get('text', '¡Me encanta!')
            self._draw_speech_bubble(img, text, (540, 1400), font_comment)
            
            # Rating grande
            rating = content_data.get('rating', 10)
            emoji = content_data.get('emoji', '😍')
            self._draw_emoji(img, emoji, (400, 1650), size=100)
            self._draw_centered_text(draw, f"{rating}/10", 750, font_rating, KIVI_GREEN_DARK)
        
        # Guardar
        filename = f"story_doggo_{content_data.get('product_name', 'producto')}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_mito_realidad(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen Mito vs Realidad"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=65, bold=True)
        font_label = self._get_font(size=55, bold=True)
        font_text = self._get_font(size=40, bold=False)
        
        # Logo
        self._draw_logo(img, position='top')
        
        myth = content_data.get('myth', 'Mito')
        reality = content_data.get('reality', 'Realidad')
        
        # LAYOUT A: Split vertical
        if layout == 'A':
            # Título
            self._draw_centered_text(draw, "MITO VS REALIDAD", 200, font_title, KIVI_TEXT_DARK)
            
            # Línea divisoria vertical
            draw.line([(540, 350), (540, 1750)], fill=KIVI_TEXT_DARK, width=8)
            
            # Lado izquierdo - MITO (rojo claro)
            draw.rectangle([(0, 350), (535, 1750)], fill=KIVI_RED_LIGHT)
            self._draw_emoji(img, "❌", (270, 450), size=100)
            self._draw_centered_text(draw, "MITO", 600, font_label, (200, 0, 0))
            self._draw_wrapped_text(draw, myth.replace("Mito: ", ""), 80, 750, 400, font_text, KIVI_TEXT_DARK)
            
            # Lado derecho - REALIDAD (verde claro)
            draw.rectangle([(545, 350), (1080, 1750)], fill=KIVI_GREEN_LIGHT_BG)
            self._draw_emoji(img, "✅", (810, 450), size=100)
            self._draw_centered_text(draw, "REALIDAD", 600, font_label, KIVI_GREEN_DARK)
            self._draw_wrapped_text(draw, reality.replace("Realidad: ", ""), 620, 750, 400, font_text, KIVI_TEXT_DARK)
        
        # LAYOUT B: Split diagonal
        elif layout == 'B':
            # Dibujar diagonal
            draw.polygon([(0, 350), (1080, 950), (1080, 1750), (0, 1150)], fill=KIVI_RED_LIGHT)
            draw.polygon([(0, 350), (1080, 350), (1080, 950), (0, 1150)], fill=KIVI_GREEN_LIGHT_BG)
            
            # Mito arriba-izquierda
            self._draw_emoji(img, "❌", (200, 500), size=80)
            self._draw_text(draw, "MITO", 320, 500, font_label, (200, 0, 0))
            self._draw_wrapped_text(draw, myth, 100, 650, 450, font_text, KIVI_TEXT_DARK)
            
            # Realidad abajo-derecha
            self._draw_emoji(img, "✅", (700, 1250), size=80)
            self._draw_text(draw, "REALIDAD", 820, 1250, font_label, KIVI_GREEN_DARK)
            self._draw_wrapped_text(draw, reality, 620, 1400, 400, font_text, KIVI_TEXT_DARK)
        
        # LAYOUT C: Arriba/abajo
        else:  # layout == 'C'
            # Título
            self._draw_centered_text(draw, "MITO VS REALIDAD", 200, font_title, KIVI_TEXT_DARK)
            
            # Mito arriba
            draw.rectangle([(100, 350), (980, 950)], fill=KIVI_RED_LIGHT)
            self._draw_emoji(img, "❌", (540, 450), size=100)
            self._draw_centered_text(draw, "MITO", 600, font_label, (200, 0, 0))
            self._draw_wrapped_text(draw, myth, 150, 730, 780, font_text, KIVI_TEXT_DARK)
            
            # Línea divisoria
            draw.line([(100, 980), (980, 980)], fill=KIVI_TEXT_DARK, width=5)
            
            # Realidad abajo
            draw.rectangle([(100, 1010), (980, 1650)], fill=KIVI_GREEN_LIGHT_BG)
            self._draw_emoji(img, "✅", (540, 1100), size=100)
            self._draw_centered_text(draw, "REALIDAD", 1240, font_label, KIVI_GREEN_DARK)
            self._draw_wrapped_text(draw, reality, 150, 1380, 780, font_text, KIVI_TEXT_DARK)
        
        # Guardar
        filename = f"story_mito_{content_data.get('product_name', 'general')}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_beneficio_dia(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen de Beneficio del Día"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=70, bold=True)
        font_headline = self._get_font(size=50, bold=False)
        font_benefit = self._get_font(size=40, bold=False)
        
        # Logo
        self._draw_logo(img, position='top')
        
        product_name = content_data.get('product_name', 'Producto')
        headline = content_data.get('headline', f'Beneficios de {product_name}')
        benefits = content_data.get('benefits', [])
        
        # LAYOUT A: Producto arriba, beneficios abajo
        if layout == 'A':
            # Título
            self._draw_centered_text(draw, "BENEFICIO DEL DÍA", 200, font_title, KIVI_GREEN_DARK)
            
            # Producto
            if product_image_url:
                self._draw_circular_product(img, product_image_url, (540, 500), radius=200)
            
            # Headline
            self._draw_centered_multiline(draw, headline, 750, 600, font_headline, KIVI_TEXT_DARK)
            
            # Beneficios
            y_pos = 950
            for benefit in benefits[:3]:
                icon = benefit.get('icon', '✓')
                name = benefit.get('name', '')
                desc = benefit.get('description', '')
                
                self._draw_emoji(img, icon, (120, y_pos), size=60)
                self._draw_text(draw, name, 220, y_pos, font_benefit, KIVI_GREEN_DARK, bold=True)
                self._draw_wrapped_text(draw, desc, 220, y_pos + 60, 800, font_benefit, KIVI_TEXT_DARK)
                y_pos += 250
        
        # LAYOUT B: Producto con blur de fondo
        elif layout == 'B':
            # Producto como fondo con blur
            if product_image_url:
                bg_img = self._download_and_open_image(product_image_url)
                if bg_img:
                    bg_img = bg_img.resize((self.story_width, self.story_height), Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=20))
                    img.paste(bg_img, (0, 0))
                    
                    # Overlay semi-transparente
                    overlay = Image.new('RGBA', (self.story_width, self.story_height), (*KIVI_BEIGE, 200))
                    img.paste(overlay, (0, 0), overlay)
            
            # Contenido
            self._draw_centered_text(draw, product_name.upper(), 300, font_title, KIVI_GREEN_DARK)
            
            y_pos = 600
            for benefit in benefits[:4]:
                self._draw_highlighted_box(img, f"{benefit.get('icon', '')} {benefit.get('name', '')}", y_pos, KIVI_GREEN_DARK)
                y_pos += 250
        
        # LAYOUT C: Grid de beneficios
        else:  # layout == 'C'
            # Título
            self._draw_centered_text(draw, product_name.upper(), 200, font_title, KIVI_GREEN_DARK)
            
            # Producto
            if product_image_url:
                self._draw_product_image(img, product_image_url, (540, 500), max_size=300)
            
            # Grid 2x2 de beneficios
            benefits_grid = benefits[:4]
            positions = [(200, 800), (680, 800), (200, 1250), (680, 1250)]
            
            for benefit, pos in zip(benefits_grid, positions):
                x, y = pos
                # Caja con beneficio
                draw.rounded_rectangle([(x-150, y-100), (x+150, y+200)], radius=20, fill=KIVI_GREEN_LIGHT_BG)
                self._draw_emoji(img, benefit.get('icon', '✓'), (x, y-50), size=70)
                self._draw_wrapped_text(draw, benefit.get('name', ''), x-130, y+50, 260, font_benefit, KIVI_TEXT_DARK, align='center')
        
        # Guardar
        filename = f"story_beneficio_{product_name}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_sabias_que(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen de Sabías Que"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=80, bold=True)
        font_fact = self._get_font(size=50, bold=False)
        font_explanation = self._get_font(size=40, bold=False)
        
        # Logo
        self._draw_logo(img, position='top')
        
        fact = content_data.get('fact', 'Sabías que...')
        explanation = content_data.get('explanation', '')
        emoji = content_data.get('emoji', '🤯')
        
        # Título
        self._draw_centered_text(draw, "SABÍAS QUE...", 200, font_title, KIVI_GREEN_DARK)
        
        # Emoji grande
        self._draw_emoji(img, emoji, (540, 400), size=150)
        
        # Dato curioso
        self._draw_centered_multiline(draw, fact.replace("Sabías que", "").strip(), 650, 700, font_fact, KIVI_TEXT_DARK)
        
        # Explicación
        self._draw_wrapped_text(draw, explanation, 100, 1100, 880, font_explanation, KIVI_GRAY)
        
        # Producto (si hay)
        if product_image_url:
            self._draw_product_image(img, product_image_url, (540, 1600), max_size=300)
        
        # Guardar
        filename = f"story_sabias_que_{content_data.get('product_name', 'general')}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_detras_camaras(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen Detrás de Cámaras (placeholder para foto real)"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_TEXT_DARK)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=70, bold=True)
        font_text = self._get_font(size=45, bold=False)
        
        # Frame tipo polaroid
        draw.rectangle([(100, 300), (980, 1500)], fill=(255, 255, 255))
        
        # Placeholder para foto
        draw.rectangle([(150, 350), (930, 1200)], fill=KIVI_BEIGE)
        self._draw_centered_text(draw, "[FOTO AQUÍ]", 800, font_title, KIVI_GRAY)
        
        # Título abajo
        title = content_data.get('title', 'Detrás de Cámaras')
        self._draw_centered_multiline(draw, title, 1280, 780, font_title, KIVI_GREEN_DARK)
        
        # Descripción
        description = content_data.get('description', '')
        self._draw_wrapped_text(draw, description, 150, 1550, 780, font_text, (255, 255, 255))
        
        # Emoji
        emoji = content_data.get('emoji', '📸')
        self._draw_emoji(img, emoji, (540, 1750), size=100)
        
        # Guardar
        filename = f"story_detras_camaras_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_cliente_semana(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen Cliente de la Semana (placeholder)"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=70, bold=True)
        font_testimonial = self._get_font(size=45, bold=False, italic=True)
        font_name = self._get_font(size=50, bold=False)
        
        # Logo
        self._draw_logo(img, position='top')
        
        # Título
        self._draw_centered_text(draw, "CLIENTE DE LA SEMANA", 200, font_title, KIVI_GREEN_DARK)
        
        # Placeholder para foto del cliente (círculo)
        draw.ellipse([(390, 400), (690, 700)], fill=KIVI_GRAY)
        self._draw_emoji(img, "👤", (540, 550), size=150)
        
        # Testimonio entre comillas
        testimonial = content_data.get('testimonial', '[Testimonio aquí]')
        self._draw_centered_text(draw, '"', 850, self._get_font(size=120, bold=False), KIVI_ORANGE)
        self._draw_wrapped_text(draw, testimonial, 150, 950, 780, font_testimonial, KIVI_TEXT_DARK, align='center')
        self._draw_centered_text(draw, '"', 1350, self._get_font(size=120, bold=False), KIVI_ORANGE)
        
        # Nombre del cliente
        client_name = content_data.get('client_name', '[Nombre]')
        self._draw_centered_text(draw, f"- {client_name}", 1500, font_name, KIVI_GREEN_DARK)
        
        # Estrellas
        rating = content_data.get('rating', 5)
        stars = '⭐' * rating
        self._draw_centered_text(draw, stars, 1600, self._get_font(size=60, bold=False), KIVI_ORANGE)
        
        # Guardar
        filename = f"story_cliente_semana_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    def _generate_desafio_receta(
        self, 
        content_data: dict, 
        product_image_url: Optional[str],
        layout: str
    ) -> str:
        """Genera imagen de Desafío/Receta"""
        
        img = Image.new('RGB', (self.story_width, self.story_height), KIVI_BEIGE)
        draw = ImageDraw.Draw(img)
        
        font_title = self._get_font(size=65, bold=True)
        font_subtitle = self._get_font(size=50, bold=False)
        font_text = self._get_font(size=40, bold=False)
        
        # Logo
        self._draw_logo(img, position='top')
        
        title = content_data.get('title', 'Receta Rápida')
        ingredients = content_data.get('ingredients', [])
        steps = content_data.get('steps', [])
        time = content_data.get('time', '15 min')
        
        # Título
        self._draw_centered_text(draw, "RECETA RÁPIDA", 200, font_title, KIVI_GREEN_DARK)
        
        # Nombre de la receta
        self._draw_centered_multiline(draw, title, 320, 600, font_subtitle, KIVI_TEXT_DARK)
        
        # Tiempo y dificultad
        self._draw_emoji(img, "⏱️", (300, 450), size=50)
        self._draw_text(draw, time, 370, 450, font_text, KIVI_TEXT_DARK)
        self._draw_emoji(img, "👨‍🍳", (650, 450), size=50)
        self._draw_text(draw, "Fácil", 720, 450, font_text, KIVI_TEXT_DARK)
        
        # Ingredientes en círculos
        if ingredients:
            y_pos = 600
            self._draw_text(draw, "Ingredientes:", 100, y_pos, font_subtitle, KIVI_GREEN_DARK, bold=True)
            y_pos += 80
            for ing in ingredients[:5]:
                self._draw_emoji(img, "•", (120, y_pos), size=30)
                self._draw_wrapped_text(draw, ing, 180, y_pos, 850, font_text, KIVI_TEXT_DARK)
                y_pos += 70
        
        # Pasos
        if steps:
            y_pos += 50
            self._draw_text(draw, "Preparación:", 100, y_pos, font_subtitle, KIVI_GREEN_DARK, bold=True)
            y_pos += 80
            for i, step in enumerate(steps[:4], 1):
                self._draw_text(draw, f"{i}.", 120, y_pos, font_text, KIVI_ORANGE, bold=True)
                self._draw_wrapped_text(draw, step, 180, y_pos, 850, font_text, KIVI_TEXT_DARK)
                y_pos += 100
        
        # Producto featured
        if product_image_url:
            self._draw_product_image(img, product_image_url, (900, 400), max_size=200)
        
        # Guardar
        filename = f"story_receta_{title.replace(' ', '_')}_{layout}.png"
        filepath = os.path.join(GENERATED_DIR, filename)
        img.save(filepath, 'PNG', quality=95)
        
        print(f"✅ Imagen generada: {filename}")
        return filepath
    
    # ========== FUNCIONES AUXILIARES ==========
    
    def _get_font(self, size: int = 40, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
        """Obtiene una fuente con el tamaño y estilo especificados"""
        try:
            if bold:
                font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            elif italic:
                font_path = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"
            else:
                font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
            
            return ImageFont.truetype(font_path, size)
        except:
            return ImageFont.load_default()
    
    def _draw_logo(self, img: Image.Image, position: str = 'top'):
        """Dibuja el logo de Kivi"""
        draw = ImageDraw.Draw(img)
        font = self._get_font(size=60, bold=True)
        
        if position == 'top':
            y = 80
        else:
            y = self.story_height - 150
        
        # Logo "kivi" con colores
        self._draw_text(draw, "k", 440, y, font, KIVI_GREEN_DARK, bold=True)
        self._draw_text(draw, "i", 490, y, font, KIVI_ORANGE, bold=True)
        self._draw_text(draw, "v", 520, y, font, KIVI_GREEN_DARK, bold=True)
        self._draw_text(draw, "i", 570, y, font, KIVI_ORANGE, bold=True)
    
    def _draw_text(
        self, 
        draw: ImageDraw.ImageDraw, 
        text: str, 
        x: int, 
        y: int, 
        font: ImageFont.FreeTypeFont, 
        color: tuple,
        bold: bool = False
    ):
        """Dibuja texto en una posición específica"""
        draw.text((x, y), text, fill=color, font=font)
    
    def _draw_centered_text(
        self, 
        draw: ImageDraw.ImageDraw, 
        text: str, 
        y: int, 
        font: ImageFont.FreeTypeFont, 
        color: tuple
    ):
        """Dibuja texto centrado horizontalmente"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.story_width - text_width) // 2
        draw.text((x, y), text, fill=color, font=font)
    
    def _draw_centered_multiline(
        self, 
        draw: ImageDraw.ImageDraw, 
        text: str, 
        y: int, 
        max_width: int, 
        font: ImageFont.FreeTypeFont, 
        color: tuple
    ):
        """Dibuja texto multilínea centrado"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for line in lines:
            self._draw_centered_text(draw, line, y, font, color)
            bbox = draw.textbbox((0, 0), line, font=font)
            y += bbox[3] - bbox[1] + 20
    
    def _draw_wrapped_text(
        self, 
        draw: ImageDraw.ImageDraw, 
        text: str, 
        x: int, 
        y: int, 
        max_width: int, 
        font: ImageFont.FreeTypeFont, 
        color: tuple,
        align: str = 'left'
    ):
        """Dibuja texto con wrapping"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for line in lines:
            if align == 'center':
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x_centered = x + (max_width - text_width) // 2
                draw.text((x_centered, y), line, fill=color, font=font)
            else:
                draw.text((x, y), line, fill=color, font=font)
            bbox = draw.textbbox((0, 0), line, font=font)
            y += bbox[3] - bbox[1] + 15
    
    def _draw_emoji(self, img: Image.Image, emoji: str, position: Tuple[int, int], size: int = 100):
        """Dibuja un emoji (simplificado como texto grande)"""
        draw = ImageDraw.Draw(img)
        font = self._get_font(size=size, bold=False)
        bbox = draw.textbbox((0, 0), emoji, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = position[0] - text_width // 2
        y = position[1] - text_height // 2
        draw.text((x, y), emoji, font=font, embedded_color=True)
    
    def _draw_product_image(
        self, 
        img: Image.Image, 
        image_url: str, 
        position: Tuple[int, int], 
        max_size: int = 400
    ):
        """Dibuja una imagen de producto"""
        product_img = self._download_and_open_image(image_url)
        if not product_img:
            return
        
        # Redimensionar manteniendo aspecto
        product_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Centrar
        x = position[0] - product_img.width // 2
        y = position[1] - product_img.height // 2
        
        # Pegar
        if product_img.mode == 'RGBA':
            img.paste(product_img, (x, y), product_img)
        else:
            img.paste(product_img, (x, y))
    
    def _draw_circular_product(
        self, 
        img: Image.Image, 
        image_url: str, 
        position: Tuple[int, int], 
        radius: int = 200
    ):
        """Dibuja una imagen de producto en forma circular"""
        product_img = self._download_and_open_image(image_url)
        if not product_img:
            return
        
        # Crear máscara circular
        mask = Image.new('L', (radius*2, radius*2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([(0, 0), (radius*2, radius*2)], fill=255)
        
        # Redimensionar producto
        product_img = product_img.resize((radius*2, radius*2), Image.Resampling.LANCZOS)
        
        # Aplicar máscara
        if product_img.mode != 'RGBA':
            product_img = product_img.convert('RGBA')
        
        output = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
        output.paste(product_img, (0, 0))
        output.putalpha(mask)
        
        # Pegar en imagen principal
        x = position[0] - radius
        y = position[1] - radius
        img.paste(output, (x, y), output)
    
    def _draw_centered_image(
        self, 
        img: Image.Image, 
        image_path: str, 
        position: Tuple[int, int], 
        max_size: int = 500
    ):
        """Dibuja una imagen centrada"""
        if not os.path.exists(image_path):
            return
        
        centered_img = Image.open(image_path)
        centered_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        x = position[0] - centered_img.width // 2
        y = position[1] - centered_img.height // 2
        
        if centered_img.mode == 'RGBA':
            img.paste(centered_img, (x, y), centered_img)
        else:
            img.paste(centered_img, (x, y))
    
    def _draw_banner(self, img: Image.Image, y: int, color: tuple, height: int = 120):
        """Dibuja un banner horizontal"""
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, y), (self.story_width, y + height)], fill=color)
    
    def _draw_highlighted_box(
        self, 
        img: Image.Image, 
        text: str, 
        y: int, 
        bg_color: tuple
    ):
        """Dibuja una caja destacada con texto"""
        draw = ImageDraw.Draw(img)
        font = self._get_font(size=45, bold=True)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Caja
        padding = 30
        box_width = text_width + padding * 2
        box_x = (self.story_width - box_width) // 2
        draw.rounded_rectangle(
            [(box_x, y - padding), (box_x + box_width, y + text_height + padding)],
            radius=20,
            fill=bg_color
        )
        
        # Texto
        text_x = (self.story_width - text_width) // 2
        draw.text((text_x, y), text, fill=(255, 255, 255), font=font)
    
    def _draw_speech_bubble(
        self, 
        img: Image.Image, 
        text: str, 
        position: Tuple[int, int], 
        font: ImageFont.FreeTypeFont
    ):
        """Dibuja un bocadillo de diálogo"""
        draw = ImageDraw.Draw(img)
        
        # Calcular tamaño del texto
        max_width = 700
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Dimensiones del bocadillo
        padding = 40
        line_height = 60
        bubble_height = len(lines) * line_height + padding * 2
        bubble_width = max_width + padding * 2
        
        x = position[0] - bubble_width // 2
        y = position[1]
        
        # Dibujar bocadillo
        draw.rounded_rectangle(
            [(x, y), (x + bubble_width, y + bubble_height)],
            radius=30,
            fill=(255, 255, 255),
            outline=KIVI_GREEN_DARK,
            width=5
        )
        
        # Dibujar texto
        text_y = y + padding
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = position[0] - text_width // 2
            draw.text((text_x, text_y), line, fill=KIVI_TEXT_DARK, font=font)
            text_y += line_height
    
    def _download_and_open_image(self, image_url: str) -> Optional[Image.Image]:
        """Descarga y abre una imagen desde URL o Base64"""
        try:
            # Detectar si es Base64
            if image_url.startswith('data:image'):
                match = re.match(r'data:image/[^;]+;base64,(.+)', image_url)
                if match:
                    image_data = base64.b64decode(match.group(1))
                    return Image.open(io.BytesIO(image_data)).convert('RGBA')
            
            # Si no, es URL HTTP/HTTPS
            response = requests.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert('RGBA')
            
        except Exception as e:
            print(f"❌ Error descargando imagen: {str(e)}")
            return None

