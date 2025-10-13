#!/usr/bin/env python3
"""
Migración: Agregar campos category y purchase_type a productos
"""
from app import create_app
from app.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Agregar columnas si no existen
    try:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE products ADD COLUMN category VARCHAR(50)'))
            conn.commit()
        print("✓ Columna 'category' agregada")
    except Exception as e:
        print(f"Columna 'category' ya existe o error: {e}")
    
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN purchase_type VARCHAR(20) DEFAULT 'detalle'"))
            conn.commit()
        print("✓ Columna 'purchase_type' agregada")
    except Exception as e:
        print(f"Columna 'purchase_type' ya existe o error: {e}")
    
    print("✓ Migración completada")

