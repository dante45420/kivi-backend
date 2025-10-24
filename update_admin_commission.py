"""
Script para actualizar la comisión del admin a 50%
(Ya que el trato es 50% vendedor, 50% admin por logística y compras)
"""
from app import create_app
from app.db import db

def update_admin_commission():
    app = create_app()
    with app.app_context():
        try:
            from app.models.user import User
            
            # Buscar el admin
            admin = User.query.filter_by(email="danteparodiwerth@gmail.com").first()
            
            if admin:
                admin.commission_rate = 0.50
                db.session.commit()
                print(f"✓ Comisión del admin actualizada a 50%")
            else:
                print("⚠ No se encontró el admin")
                
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    update_admin_commission()

