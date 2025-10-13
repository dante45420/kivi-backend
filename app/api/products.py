from flask import Blueprint, jsonify, request
from datetime import date

from ..db import db
from ..models.product import Product
from ..models.variant import ProductVariant
from ..models.catalog_price import CatalogPrice
from .auth import require_token


products_bp = Blueprint("products", __name__)


@products_bp.get("/products")
def list_products():
    items = Product.query.order_by(Product.name.asc()).all()
    result = []
    for p in items:
        row = p.to_dict()
        # Adjuntar último precio de catálogo para mostrar en la tabla (Precio/Unidad)
        c = CatalogPrice.query.filter(CatalogPrice.product_id == p.id).order_by(CatalogPrice.date.desc()).first()
        if c:
            row["catalog"] = [{"sale_price": c.sale_price, "unit": c.unit, "date": (c.date.isoformat() if c.date else None)}]
        else:
            row["catalog"] = []
        result.append(row)
    return jsonify(result)


@products_bp.get("/products/suggest")
def suggest_products():
    q = (request.args.get('q') or '').strip().lower()
    if not q:
        return jsonify([])
    def score(name: str) -> int:
        n = name.lower()
        if q == n:
            return 100
        if q in n:
            return 80
        a = set(q.split())
        b = set(n.split())
        inter = len(a & b)
        union = len(a | b) or 1
        return int(60 * inter / union)
    items = Product.query.all()
    ranked = sorted([(score(p.name), p) for p in items], key=lambda x: -x[0])
    return jsonify([{"id": p.id, "name": p.name, "score": s} for s, p in ranked if s >= 60][:5])


@products_bp.post("/products")
@require_token
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    # Require initial sale price
    try:
        sale_price = float(data.get("sale_price"))
    except (TypeError, ValueError):
        sale_price = None
    if sale_price is None or sale_price <= 0:
        return jsonify({"error": "sale_price is required and must be > 0"}), 400

    default_unit = (data.get("default_unit") or "kg").strip()
    product = Product(
        name=name,
        default_unit=default_unit,
        category=data.get("category"),
        purchase_type=data.get("purchase_type") or "detalle",
        notes=data.get("notes"),
        quality_notes=data.get("quality_notes"),
        quality_photo_url=data.get("quality_photo_url"),
    )
    db.session.add(product)
    db.session.flush()  # get product.id before creating catalog price

    catalog = CatalogPrice(
        product_id=product.id,
        date=date.today(),
        sale_price=sale_price,
        unit=default_unit or None,
    )
    db.session.add(catalog)
    # Crear variante por defecto 'kivi' con su tier de precio
    try:
        db.session.flush()
        kivi_variant = ProductVariant(product_id=product.id, label='kivi', active=True)
        db.session.add(kivi_variant)
        db.session.flush()
        # Crear tier de precio para la variante kivi con los mismos valores que el default
        from ..models.variant import VariantPriceTier
        kivi_tier = VariantPriceTier(
            product_id=product.id,
            variant_id=kivi_variant.id,
            min_qty=1.0,
            unit=default_unit,
            sale_price=sale_price
        )
        db.session.add(kivi_tier)
    except Exception as e:
        print(f"Error creando variante kivi: {e}")
        pass
    db.session.commit()
    return jsonify(product.to_dict()), 201


@products_bp.put("/products/<int:product_id>")
@require_token
def update_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True) or {}
    
    # Actualizar campos básicos
    if data.get("default_unit"):
        product.default_unit = data.get("default_unit")
    if data.get("category") is not None:
        product.category = data.get("category")
    if data.get("purchase_type") is not None:
        product.purchase_type = data.get("purchase_type")
    if "quality_notes" in data:
        product.quality_notes = data.get("quality_notes")
    if "quality_photo_url" in data:
        product.quality_photo_url = data.get("quality_photo_url")
    
    # Actualizar precio default (actualiza el más reciente o crea uno nuevo si es de otra fecha)
    try:
        if data.get("sale_price") is not None:
            sp = float(data.get("sale_price"))
            if sp > 0:
                # Buscar precio de hoy
                today_price = CatalogPrice.query.filter(
                    CatalogPrice.product_id == product.id,
                    CatalogPrice.date == date.today()
                ).first()
                
                if today_price:
                    # Actualizar precio existente de hoy
                    today_price.sale_price = sp
                    today_price.unit = product.default_unit
                else:
                    # Crear nuevo precio para hoy
                    c = CatalogPrice(
                        product_id=product.id, 
                        date=date.today(), 
                        sale_price=sp, 
                        unit=product.default_unit
                    )
                    db.session.add(c)
    except Exception:
        pass
    
    db.session.commit()
    return jsonify(product.to_dict())


@products_bp.put("/products/<int:product_id>/quality")
@require_token
def update_quality(product_id: int):
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True) or {}
    product.quality_notes = data.get("quality_notes")
    product.quality_photo_url = data.get("quality_photo_url")
    db.session.commit()
    return jsonify(product.to_dict())
