#!/usr/bin/env python3
"""
Migración para agregar campos start_date y end_date a weekly_offers
para permitir planificar ofertas futuras

Ejecutar: python migrate_add_weekly_offer_dates.py
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.db import db

app = create_app()

with app.app_context():
    print("Agregando campos start_date y end_date a weekly_offers...")
    try:
        engine = db.engine
        
        # Agregar columna start_date si no existe
        try:
            engine.execute("""
                ALTER TABLE weekly_offers 
                ADD COLUMN start_date DATETIME
            """)
            print("   ✓ Columna start_date agregada")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ️ Columna start_date ya existe")
            else:
                raise
        
        # Agregar columna end_date si no existe
        try:
            engine.execute("""
                ALTER TABLE weekly_offers 
                ADD COLUMN end_date DATETIME
            """)
            print("   ✓ Columna end_date agregada")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("   ℹ️ Columna end_date ya existe")
            else:
                raise
        
        print("\n✅ Migración completada exitosamente!")
        print("\n📝 Notas:")
        print("   - Los campos start_date y end_date permiten planificar ofertas futuras")
        print("   - Si no se especifican fechas, se usarán las ofertas más recientes")
        
    except Exception as e:
        print(f"⚠ Error: {e}")
        print("   Si las columnas ya existen, puedes ignorar este error")

