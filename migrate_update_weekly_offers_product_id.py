#!/usr/bin/env python3
"""
Migración para actualizar weekly_offers para usar product_id
Ejecutar: python migrate_update_weekly_offers_product_id.py

IMPORTANTE: Esta migración elimina los campos product_name e image_url
y agrega product_id. Si tienes ofertas existentes, necesitarás
asociarlas manualmente a productos después de ejecutar esto.
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Actualizando tabla weekly_offers...")
    
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    try:
        # Primero, eliminar ofertas existentes para evitar problemas de migración
        # (ya que no podemos mapear automáticamente product_name a product_id)
        try:
            db.session.execute(text("DELETE FROM weekly_offers"))
            print("  ✓ Ofertas existentes eliminadas (se podrán recrear después)")
        except Exception:
            print("  ℹ No hay ofertas existentes para eliminar")
        
        # Verificar si la tabla existe y tiene columnas antiguas
        if 'weekly_offers' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('weekly_offers')]
            print(f"  Columnas actuales: {', '.join(columns)}")
            
            # SQLite no soporta DROP COLUMN directamente, necesitamos recrear la tabla
            if 'product_name' in columns or 'image_url' in columns:
                print("  ℹ SQLite detectado - recreando tabla con nueva estructura...")
                # Crear tabla temporal con nueva estructura
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS weekly_offers_new (
                        id INTEGER PRIMARY KEY,
                        type VARCHAR(20) NOT NULL,
                        product_id INTEGER NOT NULL REFERENCES products(id),
                        price VARCHAR(100),
                        reference_price VARCHAR(200),
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                """))
                # Copiar datos existentes si product_id existe
                if 'product_id' in columns:
                    try:
                        db.session.execute(text("""
                            INSERT INTO weekly_offers_new (id, type, product_id, price, reference_price, created_at, updated_at)
                            SELECT id, type, product_id, price, reference_price, created_at, updated_at
                            FROM weekly_offers
                        """))
                        print("  ✓ Datos migrados a nueva tabla")
                    except Exception as e:
                        print(f"  ⚠ No se pudieron migrar datos: {e}")
                
                # Eliminar tabla antigua y renombrar nueva
                db.session.execute(text("DROP TABLE IF EXISTS weekly_offers"))
                db.session.execute(text("ALTER TABLE weekly_offers_new RENAME TO weekly_offers"))
                print("  ✓ Tabla recreada con nueva estructura")
            elif 'product_id' not in columns:
                # Solo agregar product_id si no existe
                try:
                    db.session.execute(text("ALTER TABLE weekly_offers ADD COLUMN product_id INTEGER"))
                    print("  ✓ Columna product_id agregada")
                except Exception as e:
                    print(f"  ⚠ No se pudo agregar product_id: {e}")
            else:
                print("  ✓ Tabla ya tiene la estructura correcta")
        else:
            print("  ℹ Tabla weekly_offers no existe, se creará con db.create_all()")
        
        db.session.commit()
        print("\n✓ Migración completada exitosamente")
        
        # Verificar resultado final
        if 'weekly_offers' in inspector.get_table_names():
            final_columns = [col['name'] for col in inspector.get_columns('weekly_offers')]
            print(f"  Estructura final: {', '.join(final_columns)}")
        
        print("\n📝 IMPORTANTE: Ahora debes crear las ofertas desde la página de edición")
        print("   asociándolas a productos existentes en la base de datos.")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error en la migración: {e}")
        print("  Se hizo rollback de los cambios")

