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
# Migraciones de estructura (solo agregan columnas/tablas, no borran datos)
python migrate_add_original_order_id.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_users_and_vendors.py 2>/dev/null || echo "Migración ya aplicada o error menor"
python migrate_add_vendor_system.py 2>/dev/null || echo "Migración ya aplicada o error menor"
# Migración de weekly_offers - solo agrega columnas si no existen, NO borra datos
python migrate_add_weekly_offer_dates.py 2>/dev/null || echo "Migración ya aplicada o error menor"
# Migración de social tables - solo crea tablas si no existen
python migrate_add_social_tables.py 2>/dev/null || echo "Migración ya aplicada o error menor"
# NOTA: migrate_update_weekly_offers_product_id.py NO se ejecuta automáticamente
# porque podría borrar datos. Solo ejecutar manualmente si es necesario.

echo "Build completado!"

