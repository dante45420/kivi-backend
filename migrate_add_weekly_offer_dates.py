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
        from sqlalchemy import text
        
        # Agregar columna start_date si no existe
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE weekly_offers 
                    ADD COLUMN start_date TIMESTAMP
                """))
                conn.commit()
            print("   ✓ Columna start_date agregada")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower() or "column" in str(e).lower() and "already exists" in str(e).lower():
                print("   ℹ️ Columna start_date ya existe")
            else:
                print(f"   ⚠ Error agregando start_date: {e}")
        
        # Agregar columna end_date si no existe
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE weekly_offers 
                    ADD COLUMN end_date TIMESTAMP
                """))
                conn.commit()
            print("   ✓ Columna end_date agregada")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower() or "column" in str(e).lower() and "already exists" in str(e).lower():
                print("   ℹ️ Columna end_date ya existe")
            else:
                print(f"   ⚠ Error agregando end_date: {e}")
        
        print("\n✅ Migración completada exitosamente!")
        print("\n📝 Notas:")
        print("   - Los campos start_date y end_date permiten planificar ofertas futuras")
        print("   - Si no se especifican fechas, se usarán las ofertas más recientes")
        
    except Exception as e:
        print(f"⚠ Error general: {e}")
        print("   Si las columnas ya existen, puedes ignorar este error")

