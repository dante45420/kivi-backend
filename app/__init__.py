from flask import Flask
from flask_cors import CORS

from .config import AppConfig
from .db import db


def create_app() -> Flask:
    app = Flask(__name__)

    cfg = AppConfig()
    cfg.apply(app)

    # Configuración CORS más robusta
    CORS(app, 
         origins=[cfg.cors_origin],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Token", "X-API-Token"],
         supports_credentials=False,
         max_age=3600)

    db.init_app(app)

    with app.app_context():
        from .models.product import Product  # noqa: F401
        from .models.customer import Customer  # noqa: F401
        from .models.order import Order  # noqa: F401
        from .models.order_item import OrderItem  # noqa: F401
        from .models.price_history import PriceHistory  # noqa: F401
        from .models.purchase import Purchase  # noqa: F401
        from .models.catalog_price import CatalogPrice  # noqa: F401
        from .models.competitor_price import CompetitorPrice  # noqa: F401
        from .models.vendor import Vendor  # noqa: F401
        from .models.vendor_price import VendorPrice  # noqa: F401
        from .models.charge import Charge  # noqa: F401
        from .models.payment import Payment, PaymentApplication  # noqa: F401
        from .models.inventory import InventoryLot, ProcessingRecord  # noqa: F401
        from .models.variant import ProductVariant, VariantPriceTier  # noqa: F401
        from .models.purchase_allocation import PurchaseAllocation  # noqa: F401
        db.create_all()

        from .api.auth import auth_bp
        from .api.products import products_bp
        from .api.backup import backup_bp
        from .api.orders import orders_bp
        from .api.customers import customers_bp
        from .api.prices import prices_bp
        from .api.purchases import purchases_bp
        from .api.scrape import scrape_bp
        from .api.vendors import vendors_bp
        from .api.vendor_prices import vendor_prices_bp
        from .api.charges import charges_bp
        from .api.payments import payments_bp
        from .api.inventory import inventory_bp
        from .api.variants import variants_bp
        from .api.accounting import accounting_bp
        app.register_blueprint(auth_bp, url_prefix="/api")
        app.register_blueprint(products_bp, url_prefix="/api")
        app.register_blueprint(backup_bp, url_prefix="/api")
        app.register_blueprint(orders_bp, url_prefix="/api")
        app.register_blueprint(customers_bp, url_prefix="/api")
        app.register_blueprint(prices_bp, url_prefix="/api")
        app.register_blueprint(purchases_bp, url_prefix="/api")
        app.register_blueprint(scrape_bp, url_prefix="/api")
        app.register_blueprint(vendors_bp, url_prefix="/api")
        app.register_blueprint(vendor_prices_bp, url_prefix="/api")
        app.register_blueprint(charges_bp, url_prefix="/api")
        app.register_blueprint(payments_bp, url_prefix="/api")
        app.register_blueprint(inventory_bp, url_prefix="/api")
        app.register_blueprint(variants_bp, url_prefix="/api")
        app.register_blueprint(accounting_bp, url_prefix="/api")

    # CLI
    from .cli import register_cli
    register_cli(app)

    return app
