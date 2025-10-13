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

echo "Build completado!"

