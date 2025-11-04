#!/usr/bin/env python3
"""
Migración para agregar las tablas de social media
- instagram_content
- whatsapp_messages
- content_templates
- social_schedule

Ejecutar: python migrate_add_social_tables.py
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.db import db
from app.social.models import InstagramContent, WhatsAppMessage, ContentTemplate, SocialSchedule

app = create_app()

with app.app_context():
    print("Creando tablas de social media...")
    try:
        db.create_all()
        print("✓ Tablas creadas exitosamente:")
        print("  - instagram_content")
        print("  - whatsapp_messages")
        print("  - content_templates")
        print("  - social_schedule")
        print("\n📝 Nota: Las tablas están listas para usar")
    except Exception as e:
        print(f"⚠ Error: {e}")
        print("   Si las tablas ya existen, puedes ignorar este error")

