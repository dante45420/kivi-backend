#!/usr/bin/env python3
"""
Migración: Agregar tablas para sistema de historias de Instagram
Fecha: 2025-11-04
Descripción: Crea las tablas story_templates, story_contents y story_generations
"""
import os
import sys

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import create_app
from app.db import db
from app.social.models import StoryTemplate, StoryContent, StoryGeneration

def migrate():
    """Ejecuta la migración"""
    app = create_app()
    
    with app.app_context():
        print("🔄 Iniciando migración: Agregar tablas de historias...")
        
        try:
            # Verificar si las tablas ya existen
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            tables_to_create = []
            
            if 'story_templates' not in existing_tables:
                tables_to_create.append('story_templates')
            
            if 'story_contents' not in existing_tables:
                tables_to_create.append('story_contents')
            
            if 'story_generations' not in existing_tables:
                tables_to_create.append('story_generations')
            
            if not tables_to_create:
                print("✅ Todas las tablas ya existen. No se requiere migración.")
                return
            
            print(f"📝 Creando tablas: {', '.join(tables_to_create)}")
            
            # Crear tablas
            db.create_all()
            
            print("✅ Tablas creadas exitosamente:")
            for table in tables_to_create:
                print(f"   - {table}")
            
            # Verificar que se crearon correctamente
            inspector = db.inspect(db.engine)
            existing_tables_after = inspector.get_table_names()
            
            all_created = all(table in existing_tables_after for table in tables_to_create)
            
            if all_created:
                print("\n✅ Migración completada exitosamente")
            else:
                print("\n⚠️  Advertencia: Algunas tablas no se crearon correctamente")
                
        except Exception as e:
            print(f"\n❌ Error durante la migración: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    migrate()

