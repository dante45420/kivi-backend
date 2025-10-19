"""
Migración: Agregar min_qty a vendor_product_prices para restricciones B2B
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.db import db
from sqlalchemy import text

def run_migration():
    app = create_app()
    
    with app.app_context():
        # Verificar si la columna ya existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('vendor_product_prices')]
        
        if 'min_qty' not in columns:
            print("Agregando columna min_qty a vendor_product_prices...")
            db.session.execute(text("""
                ALTER TABLE vendor_product_prices 
                ADD COLUMN min_qty FLOAT DEFAULT 1.0
            """))
            db.session.commit()
            print("✓ Columna min_qty agregada exitosamente")
        else:
            print("✓ La columna min_qty ya existe")
        
        print("\n✓ Migración completada")

if __name__ == '__main__':
    run_migration()

