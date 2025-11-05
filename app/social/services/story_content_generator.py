"""
Generador de contenido para historias de Instagram usando IA
Genera tips, mitos, datos curiosos, beneficios y contenido del perro frutero
"""
import os
import json
import random
from datetime import datetime
from typing import Dict, List, Optional
import openai
from sqlalchemy import and_

from ...db import db
from ...models.product import Product
from ..models.story_content import StoryContent


# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class StoryContentGenerator:
    """Genera contenido para historias usando IA"""
    
    def __init__(self):
        self.themes = [
            'tip_semana',
            'doggo_prueba',
            'mito_realidad',
            'beneficio_dia',
            'sabias_que',
            'detras_camaras',
            'cliente_semana',
            'desafio_receta',
        ]
    
    def generate_batch_content(
        self, 
        count: int = 8, 
        themes: Optional[List[str]] = None
    ) -> List[StoryContent]:
        """
        Genera un batch de contenidos variados
        
        Args:
            count: Cantidad de contenidos a generar
            themes: Lista de temas específicos o None para aleatorio
        
        Returns:
            Lista de StoryContent generados
        """
        generated = []
        themes_to_use = themes or self.themes
        
        # Distribuir equitativamente entre temas
        themes_distribution = []
        for i in range(count):
            themes_distribution.append(themes_to_use[i % len(themes_to_use)])
        
        # Mezclar para variedad
        random.shuffle(themes_distribution)
        
        print(f"🎨 Generando {count} contenidos: {themes_distribution}")
        
        for theme in themes_distribution:
            try:
                content = self._generate_content_for_theme(theme)
                if content:
                    generated.append(content)
                    print(f"  ✅ Generado: {theme}")
            except Exception as e:
                print(f"  ❌ Error generando {theme}: {str(e)}")
        
        return generated
    
    def _generate_content_for_theme(self, theme: str) -> Optional[StoryContent]:
        """Genera contenido para un tema específico"""
        
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
            print(f"⚠️  Tema no soportado: {theme}")
            return None
        
        return generator_func()
    
    def _generate_tip_semana(self) -> StoryContent:
        """Genera un tip de la semana"""
        
        # Obtener producto aleatorio con foto
        product = self._get_random_product_with_photo()
        
        prompt = f"""
Genera un tip útil para el cuidado y almacenamiento de {product.name if product else 'frutas y verduras'}.

El tip debe ser:
- Práctico y aplicable
- Específico para este producto
- En 2-3 puntos cortos
- Tono amigable y cercano

Formato JSON:
{{
    "title": "Cómo mantener frescos tus [producto]",
    "product_name": "{product.name if product else 'N/A'}",
    "steps": [
        "Punto 1...",
        "Punto 2...",
        "Punto 3..."
    ],
    "pro_tip": "Pro tip adicional..."
}}
"""
        
        response = self._call_openai(prompt)
        content_data = json.loads(response)
        
        # Crear registro en BD
        story_content = StoryContent(
            theme='tip_semana',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id if product else None,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_doggo_prueba(self) -> StoryContent:
        """Genera contenido del perro probando frutas"""
        
        # Obtener producto aleatorio con foto
        product = self._get_random_product_with_photo()
        
        if not product:
            print("⚠️  No hay productos con foto para Doggo")
            return None
        
        reactions = [
            {"emoji": "😍", "text": "¡Me encanta! 10/10 lo recomiendo", "rating": 10},
            {"emoji": "🤤", "text": "Delicioso! Quiero más...", "rating": 9},
            {"emoji": "😋", "text": "Muy rico! Aprobado por chef", "rating": 9},
            {"emoji": "🥰", "text": "Mi nuevo favorito!", "rating": 10},
            {"emoji": "😊", "text": "Está bueno! Lo aprobaría de nuevo", "rating": 8},
        ]
        
        reaction = random.choice(reactions)
        
        content_data = {
            "product_name": product.name,
            "emoji": reaction["emoji"],
            "text": reaction["text"],
            "rating": reaction["rating"],
            "comment": f"Hoy el chef Doggo probó {product.name} y..."
        }
        
        story_content = StoryContent(
            theme='doggo_prueba',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_mito_realidad(self) -> StoryContent:
        """Genera un mito vs realidad sobre frutas/verduras"""
        
        product = self._get_random_product_with_photo()
        product_name = product.name if product else "frutas y verduras"
        
        prompt = f"""
Genera un mito común sobre {product_name} y la realidad científica.

El contenido debe ser:
- Mito creíble que la gente piense
- Realidad basada en hechos
- Explicación breve y clara
- Tono educativo pero amigable

Formato JSON:
{{
    "myth": "Mito: [descripción del mito]",
    "reality": "Realidad: [lo que es verdad]",
    "explanation": "Explicación detallada...",
    "product_name": "{product_name}"
}}
"""
        
        response = self._call_openai(prompt)
        content_data = json.loads(response)
        
        story_content = StoryContent(
            theme='mito_realidad',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id if product else None,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_beneficio_dia(self) -> StoryContent:
        """Genera beneficios nutricionales de un producto"""
        
        product = self._get_random_product_with_photo()
        
        if not product:
            print("⚠️  No hay productos para Beneficio del Día")
            return None
        
        prompt = f"""
Lista los principales beneficios nutricionales de {product.name}.

Formato JSON:
{{
    "product_name": "{product.name}",
    "headline": "Por qué debes comer {product.name}",
    "benefits": [
        {{"icon": "💪", "name": "Vitamina X", "description": "Ayuda a..."}},
        {{"icon": "🧠", "name": "Mineral Y", "description": "Mejora..."}},
        {{"icon": "❤️", "name": "Antioxidantes", "description": "Protege..."}}
    ],
    "summary": "Resumen de 1 línea"
}}
"""
        
        response = self._call_openai(prompt)
        content_data = json.loads(response)
        
        story_content = StoryContent(
            theme='beneficio_dia',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_sabias_que(self) -> StoryContent:
        """Genera un dato curioso"""
        
        product = self._get_random_product_with_photo()
        product_name = product.name if product else "frutas y verduras"
        
        prompt = f"""
Genera un dato curioso e interesante sobre {product_name}.

Debe ser:
- Sorprendente o poco conocido
- Verificable y real
- Interesante para público general
- Tono entretenido

Formato JSON:
{{
    "fact": "Sabías que... [dato curioso]",
    "explanation": "Explicación breve del dato...",
    "product_name": "{product_name}",
    "emoji": "🤯"
}}
"""
        
        response = self._call_openai(prompt)
        content_data = json.loads(response)
        
        story_content = StoryContent(
            theme='sabias_que',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id if product else None,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_detras_camaras(self) -> StoryContent:
        """Genera contenido detrás de cámaras"""
        
        scenarios = [
            {
                "title": "Madrugada en Lo Valledor",
                "description": "Así comienza nuestro día... 5 AM seleccionando las mejores frutas para ti 🌅",
                "emoji": "🚚"
            },
            {
                "title": "El arte de elegir",
                "description": "Nuestro equipo selecciona cada producto con cuidado para garantizar calidad 🎯",
                "emoji": "🎯"
            },
            {
                "title": "Preparando tu pedido",
                "description": "Con amor y dedicación, preparamos cada caja antes de enviártela 📦",
                "emoji": "📦"
            },
        ]
        
        content_data = random.choice(scenarios)
        
        story_content = StoryContent(
            theme='detras_camaras',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=None,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_cliente_semana(self) -> StoryContent:
        """Genera placeholder para cliente de la semana (manual)"""
        
        content_data = {
            "title": "Cliente de la Semana",
            "testimonial": "[Testimonio del cliente aquí]",
            "client_name": "[Nombre del cliente]",
            "rating": 5,
            "note": "Este contenido debe ser editado manualmente con el testimonio real"
        }
        
        story_content = StoryContent(
            theme='cliente_semana',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=None,
            status='draft',  # Requiere edición manual
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _generate_desafio_receta(self) -> StoryContent:
        """Genera una receta rápida"""
        
        product = self._get_random_product_with_photo()
        
        if not product:
            print("⚠️  No hay productos para Desafío/Receta")
            return None
        
        prompt = f"""
Genera una receta rápida y fácil usando {product.name} como ingrediente principal.

La receta debe ser:
- Máximo 5 ingredientes
- Preparación en 10-15 minutos
- Pasos simples y claros
- Saludable

Formato JSON:
{{
    "title": "Nombre de la receta",
    "product_name": "{product.name}",
    "ingredients": ["Ingrediente 1", "Ingrediente 2", "..."],
    "steps": ["Paso 1", "Paso 2", "..."],
    "time": "10 minutos",
    "difficulty": "Fácil"
}}
"""
        
        response = self._call_openai(prompt)
        content_data = json.loads(response)
        
        story_content = StoryContent(
            theme='desafio_receta',
            content_data=json.dumps(content_data, ensure_ascii=False),
            product_id=product.id,
            status='ready',
            generated_by='ai'
        )
        
        db.session.add(story_content)
        db.session.commit()
        
        return story_content
    
    def _get_random_product_with_photo(self) -> Optional[Product]:
        """Obtiene un producto aleatorio que tenga foto"""
        products = Product.query.filter(
            Product.quality_photo_url.isnot(None),
            Product.quality_photo_url != ''
        ).all()
        
        if not products:
            return None
        
        return random.choice(products)
    
    def _call_openai(self, prompt: str) -> str:
        """Llama a OpenAI GPT para generar contenido"""
        
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY no configurada")
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en frutas, verduras y nutrición. Generas contenido educativo y entretenido para redes sociales de una frutería llamada Kivi. Tu tono es amigable, cercano y profesional. Siempre respondes en formato JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Limpiar markdown code blocks si existen
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return content.strip()
            
        except Exception as e:
            print(f"❌ Error llamando a OpenAI: {str(e)}")
            raise
    
    def check_for_duplicates(self, content_data: dict, theme: str) -> bool:
        """Verifica si ya existe contenido similar"""
        
        # Buscar contenidos del mismo tema
        existing = StoryContent.query.filter_by(
            theme=theme,
            status='ready'
        ).all()
        
        # Comparación simple - podría mejorarse con embeddings
        for existing_content in existing:
            existing_data = json.loads(existing_content.content_data)
            
            # Comparar campos clave según el tema
            if theme == 'tip_semana' and existing_data.get('title') == content_data.get('title'):
                return True
            elif theme == 'mito_realidad' and existing_data.get('myth') == content_data.get('myth'):
                return True
            elif theme == 'sabias_que' and existing_data.get('fact') == content_data.get('fact'):
                return True
        
        return False

