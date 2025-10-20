#!/usr/bin/env python3
"""
Migración: Eliminar tablas innecesarias del sistema B2B viejo, vendors e inventory
"""
import sys
from app import create_app
from app.db import db

def migrate():
    app = create_app()
    with app.app_context():
        # Lista de tablas a eliminar
        tables_to_drop = [
            'purchase_allocations',
            'inventory_lots',
            'processing_records',
            'vendor_product_prices',
            'vendor_prices',
            'vendors',
            'competitor_prices',
            'merchant_order_items',
            'merchant_orders',
            'merchant_users',
        ]
        
        print("🗑️  Iniciando eliminación de tablas innecesarias...")
        
        for table_name in tables_to_drop:
            try:
                # Verificar si la tabla existe
                result = db.session.execute(db.text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                ))
                if result.fetchone():
                    print(f"   ⏳ Eliminando tabla: {table_name}")
                    db.session.execute(db.text(f"DROP TABLE IF EXISTS {table_name}"))
                    print(f"   ✅ Tabla {table_name} eliminada")
                else:
                    print(f"   ℹ️  Tabla {table_name} no existe (ya fue eliminada)")
            except Exception as e:
                print(f"   ⚠️  Error eliminando {table_name}: {e}")
                # No hacer rollback, continuar con las demás tablas
        
        db.session.commit()
        print("\n✅ Migración completada exitosamente!")
        print("\n📊 Resumen:")
        print("   - Eliminadas tablas de sistema B2B viejo (merchant_*, vendor_product_prices)")
        print("   - Eliminadas tablas de vendors (vendors, vendor_prices)")
        print("   - Eliminadas tablas de inventory (inventory_lots, processing_records)")
        print("   - Eliminadas tablas de asignaciones (purchase_allocations)")
        print("   - Eliminadas tablas de competidores (competitor_prices)")

if __name__ == '__main__':
    migrate()

