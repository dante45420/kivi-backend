from flask import Flask, request
from flask_cors import CORS

from .config import AppConfig
from .db import db


def create_app() -> Flask:
    app = Flask(__name__)

    cfg = AppConfig()
    cfg.apply(app)

    # Configuración CORS más robusta
    CORS(app, 
         origins=cfg.cors_origins,
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Token", "X-API-Token"],
         supports_credentials=False,
         max_age=3600)
    
    # Asegurar que TODAS las respuestas (incluso errores) tengan headers CORS
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get('Origin')
        if origin and origin in cfg.cors_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Token, X-API-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Credentials'] = 'false'
        return response

    db.init_app(app)

    with app.app_context():
        from .models.product import Product  # noqa: F401
        from .models.customer import Customer  # noqa: F401
        from .models.order import Order  # noqa: F401
        from .models.order_item import OrderItem  # noqa: F401
        from .models.price_history import PriceHistory  # noqa: F401
        from .models.purchase import Purchase  # noqa: F401
        from .models.catalog_price import CatalogPrice  # noqa: F401
        from .models.charge import Charge  # noqa: F401
        from .models.payment import Payment, PaymentApplication  # noqa: F401
        from .models.variant import ProductVariant, VariantPriceTier  # noqa: F401
        from .models.weekly_offer import WeeklyOffer  # noqa: F401
        db.create_all()

        from .api.auth import auth_bp
        from .api.products import products_bp
        from .api.backup import backup_bp
        from .api.orders import orders_bp
        from .api.customers import customers_bp
        from .api.purchases import purchases_bp
        from .api.charges import charges_bp
        from .api.payments import payments_bp
        from .api.variants import variants_bp
        from .api.accounting import accounting_bp
        from .api.admin_kpis import admin_kpis_bp
        from .api.weekly_offers import weekly_offers_bp
        app.register_blueprint(auth_bp, url_prefix="/api")
        app.register_blueprint(products_bp, url_prefix="/api")
        app.register_blueprint(backup_bp, url_prefix="/api")
        app.register_blueprint(orders_bp, url_prefix="/api")
        app.register_blueprint(customers_bp, url_prefix="/api")
        app.register_blueprint(purchases_bp, url_prefix="/api")
        app.register_blueprint(charges_bp, url_prefix="/api")
        app.register_blueprint(payments_bp, url_prefix="/api")
        app.register_blueprint(variants_bp, url_prefix="/api")
        app.register_blueprint(accounting_bp, url_prefix="/api")
        app.register_blueprint(admin_kpis_bp, url_prefix="/api")
        app.register_blueprint(weekly_offers_bp, url_prefix="/api")

    # CLI
    from .cli import register_cli
    register_cli(app)

    return app
