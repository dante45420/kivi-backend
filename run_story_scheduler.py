#!/usr/bin/env python3
"""
Script para ejecutar el Story Scheduler manualmente o desde cron
Uso: python run_story_scheduler.py
"""
import os
import sys

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app import create_app
from app.social.services.story_scheduler import run_scheduler

def main():
    """Ejecuta el scheduler"""
    print("🚀 Story Scheduler - Iniciando...")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        result = run_scheduler()
        
        print("\n" + "=" * 60)
        print("📊 RESULTADO:")
        print("=" * 60)
        
        if result['ran']:
            print(f"✅ Generación ejecutada")
            print(f"   Semana objetivo: {result['target_week']}")
            if result['result'] and result['result']['success']:
                print(f"   Historias generadas: {result['result']['generated_count']}")
                print(f"   Batch ID: {result['result']['batch_id']}")
            else:
                print(f"   ❌ Error: {result['result']['message'] if result['result'] else 'Desconocido'}")
        else:
            print(f"⏭️  No se ejecutó: {result['reason']}")
            if result['target_week']:
                print(f"   Semana objetivo: {result['target_week']}")
        
        print("=" * 60)
        
        # Exit code para scripts de cron
        return 0 if (not result['ran'] or (result['result'] and result['result']['success'])) else 1

if __name__ == "__main__":
    sys.exit(main())

