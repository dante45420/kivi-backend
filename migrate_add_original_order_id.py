#!/usr/bin/env python3
"""
Migración para agregar columna original_order_id a la tabla charges
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        from app.db import db
        
        print("🔄 Agregando columna 'original_order_id' a la tabla 'charges'...")
        
        try:
            # Agregar columna original_order_id a charges
            db.session.execute(text("""
                ALTER TABLE charges 
                ADD COLUMN original_order_id INTEGER REFERENCES orders(id);
            """))
            db.session.commit()
            print("   ✅ Columna 'original_order_id' agregada exitosamente")
            
        except Exception as e:
            db.session.rollback()
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("   ℹ️  Columna 'original_order_id' ya existe en 'charges'")
            else:
                print(f"   ❌ Error: {e}")
                raise

if __name__ == "__main__":
    migrate()
