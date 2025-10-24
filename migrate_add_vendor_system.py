#!/usr/bin/env python3
"""
Migración: Agregar sistema de vendedores
- Agrega tabla 'users' para vendedores y admin
- Agrega columna 'vendor_id' a la tabla 'orders'
- Agrega columna 'vendor_id' a la tabla 'customers'
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
        print("🔄 Iniciando migración del sistema de vendedores...")
        
        try:
            # 1. Crear tabla users si no existe
            print("\n📋 Paso 1: Verificando tabla 'users'...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'vendor',
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    commission_rate FLOAT NOT NULL DEFAULT 0.50
                );
            """))
            db.session.commit()
            print("   ✅ Tabla 'users' lista")
            
            # 2. Agregar índice en email si no existe
            print("\n📋 Paso 2: Verificando índice en users.email...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
            """))
            db.session.commit()
            print("   ✅ Índice creado")
            
            # 3. Agregar vendor_id a orders
            print("\n📋 Paso 3: Agregando vendor_id a tabla 'orders'...")
            try:
                db.session.execute(text("""
                    ALTER TABLE orders 
                    ADD COLUMN vendor_id INTEGER REFERENCES users(id);
                """))
                db.session.commit()
                print("   ✅ Columna 'vendor_id' agregada a 'orders'")
            except Exception as e:
                db.session.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("   ℹ️  Columna 'vendor_id' ya existe en 'orders'")
                else:
                    raise
            
            # 4. Agregar vendor_id a customers
            print("\n📋 Paso 4: Agregando vendor_id a tabla 'customers'...")
            try:
                db.session.execute(text("""
                    ALTER TABLE customers 
                    ADD COLUMN vendor_id INTEGER REFERENCES users(id);
                """))
                db.session.commit()
                print("   ✅ Columna 'vendor_id' agregada a 'customers'")
            except Exception as e:
                db.session.rollback()
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("   ℹ️  Columna 'vendor_id' ya existe en 'customers'")
                else:
                    raise
            
            # 5. Verificar si hay usuarios creados
            print("\n📋 Paso 5: Verificando usuarios existentes...")
            result = db.session.execute(text("SELECT COUNT(*) FROM users;"))
            user_count = result.fetchone()[0]
            print(f"   ℹ️  Usuarios registrados: {user_count}")
            
            if user_count == 0:
                print("\n   ⚠️  No hay usuarios registrados.")
                print("   💡 Para crear un usuario admin, ejecuta:")
                print("      python backend/create_merchant_user.py")
            
            print("\n✅ Migración completada exitosamente!")
            print("\n📝 Resumen:")
            print("   - Tabla 'users' creada/verificada")
            print("   - Columna 'vendor_id' agregada a 'orders'")
            print("   - Columna 'vendor_id' agregada a 'customers'")
            print("\n🎯 El sistema de vendedores está listo para usar")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error durante la migración: {e}")
            print("\n💡 Si el error persiste, verifica:")
            print("   1. Que la base de datos esté accesible")
            print("   2. Que tengas permisos para modificar tablas")
            print("   3. Los logs completos del error arriba")
            sys.exit(1)

if __name__ == "__main__":
    run_migration()

