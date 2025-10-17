#!/usr/bin/env python3
"""
Migración: Sistema de Comerciantes (B2B)
- merchant_users
- merchant_orders
- merchant_order_items
- vendor_product_prices
"""

from app import create_app
from app.db import db

def run_migration():
    app = create_app()
    with app.app_context():
        print("📦 Iniciando migración del sistema de comerciantes...")
        
        try:
            # 1. Tabla de usuarios comerciantes
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS merchant_users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    business_name VARCHAR(200) NOT NULL,
                    contact_name VARCHAR(200),
                    phone VARCHAR(50),
                    address TEXT,
                    rut VARCHAR(50),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP
                )
            """)
            print("✓ Tabla merchant_users creada")
            
            # 2. Tabla de precios de proveedores
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS vendor_product_prices (
                    id SERIAL PRIMARY KEY,
                    vendor_id INTEGER REFERENCES vendors(id) NOT NULL,
                    product_id INTEGER REFERENCES products(id) NOT NULL,
                    variant_id INTEGER REFERENCES product_variants(id),
                    price_per_kg FLOAT,
                    price_per_unit FLOAT,
                    unit VARCHAR(20) NOT NULL,
                    markup_percentage FLOAT DEFAULT 20.0,
                    final_price FLOAT NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE,
                    last_updated TIMESTAMP DEFAULT NOW(),
                    source VARCHAR(50) DEFAULT 'auto',
                    UNIQUE(vendor_id, product_id, variant_id)
                )
            """)
            print("✓ Tabla vendor_product_prices creada")
            
            # 3. Tabla de pedidos de comerciantes
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS merchant_orders (
                    id SERIAL PRIMARY KEY,
                    merchant_user_id INTEGER REFERENCES merchant_users(id) NOT NULL,
                    order_number VARCHAR(100) UNIQUE,
                    status VARCHAR(50) DEFAULT 'pending',
                    subtotal FLOAT DEFAULT 0,
                    delivery_fee FLOAT DEFAULT 0,
                    total_amount FLOAT DEFAULT 0,
                    delivery_address TEXT,
                    delivery_date DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("✓ Tabla merchant_orders creada")
            
            # 4. Tabla de items de pedidos
            db.session.execute("""
                CREATE TABLE IF NOT EXISTS merchant_order_items (
                    id SERIAL PRIMARY KEY,
                    merchant_order_id INTEGER REFERENCES merchant_orders(id) NOT NULL,
                    product_id INTEGER REFERENCES products(id) NOT NULL,
                    variant_id INTEGER REFERENCES product_variants(id),
                    qty FLOAT NOT NULL,
                    unit VARCHAR(20) NOT NULL,
                    price_per_unit FLOAT NOT NULL,
                    subtotal FLOAT NOT NULL,
                    preferred_vendor_id INTEGER REFERENCES vendors(id),
                    assigned_vendor_id INTEGER REFERENCES vendors(id),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("✓ Tabla merchant_order_items creada")
            
            # 5. Índices para performance
            db.session.execute("""
                CREATE INDEX IF NOT EXISTS idx_vendor_prices_vendor 
                ON vendor_product_prices(vendor_id)
            """)
            db.session.execute("""
                CREATE INDEX IF NOT EXISTS idx_vendor_prices_product 
                ON vendor_product_prices(product_id)
            """)
            db.session.execute("""
                CREATE INDEX IF NOT EXISTS idx_merchant_orders_user 
                ON merchant_orders(merchant_user_id)
            """)
            db.session.execute("""
                CREATE INDEX IF NOT EXISTS idx_merchant_orders_status 
                ON merchant_orders(status)
            """)
            print("✓ Índices creados")
            
            # 6. Crear proveedor "Lo Valledor" por defecto si no existe
            from app.models.vendor import Vendor
            lo_valledor = Vendor.query.filter_by(name='Lo Valledor').first()
            if not lo_valledor:
                lo_valledor = Vendor(
                    name='Lo Valledor',
                    contact='Mercado Central',
                    phone='',
                    email=''
                )
                db.session.add(lo_valledor)
                print("✓ Proveedor 'Lo Valledor' creado")
            else:
                print("✓ Proveedor 'Lo Valledor' ya existe")
            
            db.session.commit()
            print("✅ Migración completada exitosamente")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            raise

if __name__ == "__main__":
    run_migration()

