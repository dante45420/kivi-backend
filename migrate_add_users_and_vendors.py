"""
Script de migración para agregar:
1. Tabla de usuarios (users)
2. Campo vendor_id a customers
3. Campo vendor_id a orders
"""
import sys
import os
from werkzeug.security import generate_password_hash

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.db import db

def migrate():
    app = create_app()
    
    with app.app_context():
        print("🔧 Ejecutando migración: agregar users y vendor_id...")
        
        # Obtener el motor de la base de datos
        engine = db.engine
        
        # 1. Crear tabla users
        print("\n1️⃣ Creando tabla users...")
        try:
            engine.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'vendor',
                    active BOOLEAN NOT NULL DEFAULT 1,
                    commission_rate FLOAT NOT NULL DEFAULT 0.75,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Tabla users creada")
        except Exception as e:
            print(f"   ⚠️ Error creando tabla users (puede que ya exista): {e}")
        
        # 2. Crear índice en email
        try:
            engine.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            print("   ✓ Índice en email creado")
        except Exception as e:
            print(f"   ⚠️ Error creando índice: {e}")
        
        # 3. Agregar campo vendor_id a customers
        print("\n2️⃣ Agregando vendor_id a customers...")
        try:
            engine.execute("ALTER TABLE customers ADD COLUMN vendor_id INTEGER")
            print("   ✓ Campo vendor_id agregado a customers")
        except Exception as e:
            print(f"   ⚠️ Campo vendor_id ya existe en customers o error: {e}")
        
        # 4. Agregar índice en vendor_id de customers
        try:
            engine.execute("CREATE INDEX IF NOT EXISTS idx_customers_vendor ON customers(vendor_id)")
            print("   ✓ Índice en vendor_id de customers creado")
        except Exception as e:
            print(f"   ⚠️ Error creando índice: {e}")
        
        # 5. Agregar campo vendor_id a orders
        print("\n3️⃣ Agregando vendor_id a orders...")
        try:
            engine.execute("ALTER TABLE orders ADD COLUMN vendor_id INTEGER")
            print("   ✓ Campo vendor_id agregado a orders")
        except Exception as e:
            print(f"   ⚠️ Campo vendor_id ya existe en orders o error: {e}")
        
        # 6. Agregar índice en vendor_id de orders
        try:
            engine.execute("CREATE INDEX IF NOT EXISTS idx_orders_vendor ON orders(vendor_id)")
            print("   ✓ Índice en vendor_id de orders creado")
        except Exception as e:
            print(f"   ⚠️ Error creando índice: {e}")
        
        # 7. Crear usuario admin por defecto
        print("\n4️⃣ Creando usuario admin por defecto...")
        try:
            from app.models.user import User
            
            # Verificar si ya existe un admin
            admin = User.query.filter_by(email="danteparodiwerth@gmail.com").first()
            
            if not admin:
                admin = User(
                    email="danteparodiwerth@gmail.com",
                    name="Admin Kivi",
                    role="admin",
                    active=True,
                    commission_rate=0.50  # Admin se queda con 50% de la ganancia (logística y compras)
                )
                admin.set_password("Dante454@")
                db.session.add(admin)
                db.session.commit()
                print(f"   ✓ Usuario admin creado (ID: {admin.id})")
            else:
                # Actualizar comisión del admin si ya existe
                if admin.commission_rate != 0.50:
                    admin.commission_rate = 0.50
                    db.session.commit()
                    print(f"   ✓ Admin ya existe, comisión actualizada a 50% (ID: {admin.id})")
                else:
                    print(f"   ℹ️ Usuario admin ya existe (ID: {admin.id})")
            
            # Actualizar comisión de vendedores existentes a 50% si tienen 75%
            vendors = User.query.filter_by(role='vendor').all()
            if vendors:
                for vendor in vendors:
                    if vendor.commission_rate == 0.75:
                        vendor.commission_rate = 0.50
                        db.session.commit()
                        print(f"   ✓ Comisión de {vendor.name} actualizada de 75% a 50%")
        except Exception as e:
            print(f"   ⚠️ Error creando usuario admin: {e}")
            db.session.rollback()
        
        print("\n✅ Migración completada exitosamente!")
        print("\n📝 Notas:")
        print("   - Los clientes y pedidos existentes no tienen vendor_id asignado (NULL)")
        print("   - Puedes asignar vendedores manualmente o desde la interfaz")
        print("   - Usuario admin: danteparodiwerth@gmail.com / Dante454@")
        print("   - Comisión por defecto para vendedores: 50% (el otro 50% es para admin)")


if __name__ == "__main__":
    migrate()

