#!/usr/bin/env python3
"""
Script para crear usuario comerciante de prueba en producción
"""

from app import create_app
from app.db import db
from app.models.merchant_user import MerchantUser

def create_test_merchant():
    app = create_app()
    with app.app_context():
        # Verificar si ya existe
        existing = MerchantUser.query.filter_by(email='mateoquintas@gmail.com').first()
        if existing:
            print(f"✓ Usuario ya existe: {existing.email}")
            print(f"   ID: {existing.id}")
            print(f"   Negocio: {existing.business_name}")
            return
        
        # Crear nuevo usuario
        user = MerchantUser(
            email='mateoquintas@gmail.com',
            business_name='Negocio de Prueba',
            contact_name='Mateo Quintas',
            phone='+56912345678',
            address='Dirección de prueba',
            rut='12345678-9',
            is_active=True
        )
        user.set_password('Prueba123')
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Usuario comerciante creado exitosamente:")
        print(f"   Email: {user.email}")
        print(f"   Negocio: {user.business_name}")
        print(f"   Contraseña: Prueba123")
        print(f"   ID: {user.id}")

if __name__ == "__main__":
    create_test_merchant()

