"""
API para gestión de proveedores y precios (Admin)
"""
from flask import Blueprint, jsonify, request
from datetime import datetime

from ..db import db
from ..models.vendor import Vendor
from ..models.vendor_product_price import VendorProductPrice
from ..models.product import Product
from ..models.variant import ProductVariant
from .auth import require_token


admin_vendors_bp = Blueprint("admin_vendors", __name__)


@admin_vendors_bp.get("/admin/vendors/prices")
@require_token
def list_all_vendor_prices():
    """Listar todos los precios de proveedores"""
    vendor_id = request.args.get('vendor_id', type=int)
    product_id = request.args.get('product_id', type=int)
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    
    query = VendorProductPrice.query
    
    if vendor_id:
        query = query.filter_by(vendor_id=vendor_id)
    if product_id:
        query = query.filter_by(product_id=product_id)
    if available_only:
        query = query.filter_by(is_available=True)
    
    prices = query.order_by(VendorProductPrice.last_updated.desc()).all()
    
    # Enriquecer con info de vendor, product, variant
    result = []
    for p in prices:
        vendor = Vendor.query.get(p.vendor_id)
        product = Product.query.get(p.product_id)
        variant = ProductVariant.query.get(p.variant_id) if p.variant_id else None
        
        item = p.to_dict()
        item['vendor_name'] = vendor.name if vendor else None
        item['product_name'] = product.name if product else None
        item['variant_label'] = variant.label if variant else None
        result.append(item)
    
    return jsonify(result)


@admin_vendors_bp.get("/admin/vendors/<int:vendor_id>/prices")
@require_token
def get_vendor_prices(vendor_id: int):
    """Precios de un proveedor específico"""
    vendor = Vendor.query.get_or_404(vendor_id)
    prices = VendorProductPrice.query.filter_by(vendor_id=vendor_id).all()
    
    result = []
    for p in prices:
        product = Product.query.get(p.product_id)
        variant = ProductVariant.query.get(p.variant_id) if p.variant_id else None
        
        item = p.to_dict()
        item['product_name'] = product.name if product else None
        item['variant_label'] = variant.label if variant else None
        result.append(item)
    
    return jsonify({
        'vendor': vendor.to_dict(),
        'prices': result
    })


@admin_vendors_bp.post("/admin/vendors/<int:vendor_id>/prices")
@require_token
def create_vendor_price(vendor_id: int):
    """Crear precio manualmente"""
    data = request.get_json() or {}
    
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    unit = data.get('unit', 'kg')
    cost_price = float(data.get('cost_price', 0))
    markup = float(data.get('markup_percentage', 20))
    
    if not product_id or cost_price <= 0:
        return jsonify({'error': 'product_id y cost_price son requeridos'}), 400
    
    # Calcular precio final
    final_price = cost_price * (1 + markup / 100)
    
    # Verificar si ya existe
    existing = VendorProductPrice.query.filter_by(
        vendor_id=vendor_id,
        product_id=product_id,
        variant_id=variant_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Este precio ya existe. Usa PUT para actualizar.'}), 400
    
    price = VendorProductPrice(
        vendor_id=vendor_id,
        product_id=product_id,
        variant_id=variant_id,
        unit=unit,
        price_per_kg=cost_price if unit == 'kg' else None,
        price_per_unit=cost_price if unit == 'unit' else None,
        markup_percentage=markup,
        final_price=final_price,
        source='manual',
        is_available=True
    )
    
    db.session.add(price)
    db.session.commit()
    
    return jsonify(price.to_dict()), 201


@admin_vendors_bp.put("/admin/vendors/prices/<int:price_id>")
@require_token
def update_vendor_price(price_id: int):
    """Actualizar precio"""
    price = VendorProductPrice.query.get_or_404(price_id)
    data = request.get_json() or {}
    
    if 'cost_price' in data:
        cost_price = float(data['cost_price'])
        markup = float(data.get('markup_percentage', price.markup_percentage))
        
        price.markup_percentage = markup
        final_price = cost_price * (1 + markup / 100)
        
        if price.unit == 'kg':
            price.price_per_kg = cost_price
        else:
            price.price_per_unit = cost_price
        
        price.final_price = final_price
    
    if 'markup_percentage' in data and 'cost_price' not in data:
        markup = float(data['markup_percentage'])
        cost_price = price.price_per_kg or price.price_per_unit
        price.markup_percentage = markup
        price.final_price = cost_price * (1 + markup / 100)
    
    if 'is_available' in data:
        price.is_available = bool(data['is_available'])
    
    price.last_updated = datetime.utcnow()
    price.source = 'manual'
    
    db.session.commit()
    return jsonify(price.to_dict())


@admin_vendors_bp.delete("/admin/vendors/prices/<int:price_id>")
@require_token
def delete_vendor_price(price_id: int):
    """Eliminar precio"""
    price = VendorProductPrice.query.get_or_404(price_id)
    db.session.delete(price)
    db.session.commit()
    return jsonify({'message': 'Precio eliminado'}), 200


@admin_vendors_bp.patch("/admin/vendors/prices/<int:price_id>/toggle")
@require_token
def toggle_availability(price_id: int):
    """Toggle disponibilidad con un click"""
    price = VendorProductPrice.query.get_or_404(price_id)
    price.is_available = not price.is_available
    price.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify(price.to_dict())

