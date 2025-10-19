"""
API de productos para comerciantes (catálogo B2B con precios especiales)
"""
from flask import Blueprint, jsonify, request

from ..db import db
from ..models.product import Product
from ..models.variant import ProductVariant
from ..models.vendor_product_price import VendorProductPrice
from ..models.vendor import Vendor


merchant_products_bp = Blueprint("merchant_products", __name__)


def require_merchant_token(func):
    """Decorator para validar token de comerciante"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('X-API-Token') or request.headers.get('X-Merchant-Token')
        
        if not token or not token.startswith('merchant_'):
            return jsonify({'error': 'No autorizado'}), 401
        
        try:
            user_id = int(token.replace('merchant_', ''))
            from ..models.merchant_user import MerchantUser
            user = MerchantUser.query.get(user_id)
            
            if not user or not user.is_active:
                return jsonify({'error': 'No autorizado'}), 401
            
            # Pasar el usuario al endpoint
            return func(user, *args, **kwargs)
        except:
            return jsonify({'error': 'No autorizado'}), 401
    
    return wrapper


@merchant_products_bp.get("/merchant/products")
@require_merchant_token
def get_merchant_products(user):
    """
    Catálogo de productos disponibles para comerciantes con precios B2B
    """
    try:
        # Obtener todos los precios disponibles agrupados por producto
        prices = VendorProductPrice.query.filter_by(is_available=True).all()
        
        # Agrupar por producto
        products_dict = {}
        
        for price in prices:
            product_id = price.product_id
            
            if product_id not in products_dict:
                product = Product.query.get(product_id)
                if not product:
                    continue
                
                products_dict[product_id] = {
                    'id': product.id,
                    'name': product.name,
                    'category': product.category,
                    'default_unit': product.default_unit,
                    'image_url': product.quality_photo_url,
                    'variants': [],
                    'vendors': []
                }
            
            # Agregar información del precio
            vendor_info = {
                'vendor_id': price.vendor_id,
                'vendor_name': price.vendor_name,
                'variant_id': price.variant_id,
                'variant_label': price.variant_label,
                'unit': price.unit,
                'price': price.final_price,
                'last_updated': price.last_updated.isoformat() if price.last_updated else None
            }
            
            products_dict[product_id]['vendors'].append(vendor_info)
        
        # Convertir a lista
        result = list(products_dict.values())
        
        # Ordenar por categoría y nombre
        result.sort(key=lambda x: (x['category'] or 'zzz', x['name']))
        
        return jsonify(result), 200
    
    except Exception as e:
        print(f"Error en get_merchant_products: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@merchant_products_bp.get("/merchant/vendors")
@require_merchant_token
def get_merchant_vendors(user):
    """Lista de proveedores disponibles"""
    try:
        vendors = Vendor.query.all()
        return jsonify([{
            'id': v.id,
            'name': v.name,
            'contact': v.contact,
            'phone': v.phone
        } for v in vendors]), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

