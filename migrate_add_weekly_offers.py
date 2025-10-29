#!/usr/bin/env python3
"""
Migración para agregar la tabla weekly_offers
Ejecutar: python migrate_add_weekly_offers.py
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.db import db
from app.models.weekly_offer import WeeklyOffer

app = create_app()

with app.app_context():
    print("Creando tabla weekly_offers...")
    try:
        db.create_all()
        print("✓ Tabla weekly_offers creada exitosamente")
        print("\n📝 Nota: La tabla usa product_id para asociar ofertas a productos")
        print("   Las fotos se toman del campo quality_photo_url del producto")
    except Exception as e:
        print(f"⚠ Error: {e}")
        print("   Si la tabla ya existe, puedes usar migrate_update_weekly_offers_product_id.py")

