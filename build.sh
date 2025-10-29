#!/usr/bin/env bash
# Script de build para Render

set -e

echo "Instalando dependencias..."
pip install -r requirements.txt

echo "Inicializando base de datos..."
python -c "
from app import create_app
from app.db import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Base de datos inicializada correctamente')
"

echo "Ejecutando migraciones..."
python migrate_add_category.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_original_order_id.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_merchant_system.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_users_and_vendors.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_vendor_system.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_weekly_offers.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_update_weekly_offers_product_id.py 2>/dev/null || echo "Migración ya aplicada o error menor"

echo "Creando usuario comerciante de prueba..."
python migrate_create_test_merchant.py 2>/dev/null || echo "Usuario ya existe o error menor"

echo "Build completado!"

