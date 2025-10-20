"""
Endpoint temporal para ejecutar migración min_qty en producción
"""
from flask import Blueprint, jsonify
from app.db import db
from sqlalchemy import text, inspect

migration_bp = Blueprint('migration', __name__)

@migration_bp.route('/admin/migration/add-min-qty', methods=['POST'])
def add_min_qty_column():
    """
    Endpoint temporal para agregar columna min_qty a vendor_product_prices
    Solo para uso en producción/staging
    """
    try:
        # Verificar si la columna ya existe
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('vendor_product_prices')]
        
        if 'min_qty' not in columns:
            # Agregar columna
            db.session.execute(text("""
                ALTER TABLE vendor_product_prices 
                ADD COLUMN min_qty FLOAT DEFAULT 1.0
            """))
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Columna min_qty agregada exitosamente',
                'columns': sorted(columns + ['min_qty'])
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': 'La columna min_qty ya existe',
                'columns': sorted(columns)
            }), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@migration_bp.route('/admin/migration/verify-min-qty', methods=['GET'])
def verify_min_qty_column():
    """
    Verificar si la columna min_qty existe
    """
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('vendor_product_prices')]
        
        return jsonify({
            'success': True,
            'has_min_qty': 'min_qty' in columns,
            'all_columns': sorted(columns)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

