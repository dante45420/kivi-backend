#!/usr/bin/env python3
"""
Migración: Agregar campo original_order_id a charges
"""
from app import create_app
from app.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Agregar columna si no existe
    try:
        with db.engine.connect() as conn:
            # Agregar columna original_order_id
            conn.execute(text('ALTER TABLE charges ADD COLUMN original_order_id INTEGER REFERENCES orders(id)'))
            conn.commit()
        print("✓ Columna 'original_order_id' agregada a 'charges'")
    except Exception as e:
        print(f"Columna 'original_order_id' ya existe o error: {e}")
    
    # Inicializar original_order_id con el valor de order_id para cargos existentes
    try:
        with db.engine.connect() as conn:
            conn.execute(text('UPDATE charges SET original_order_id = order_id WHERE original_order_id IS NULL'))
            conn.commit()
        print("✓ Inicializados valores de 'original_order_id'")
    except Exception as e:
        print(f"Error inicializando valores: {e}")
    
    print("✓ Migración completada")

