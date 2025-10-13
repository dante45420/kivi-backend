import click
from flask import current_app
from flask_sqlalchemy import SQLAlchemy


def register_admin_commands(app):
    @app.cli.command("db-reset")
    @click.option("--yes", is_flag=True, help="Confirma el reseteo sin preguntar")
    def db_reset(yes):
        """Elimina y recrea todas las tablas (¡destructivo!)."""
        if not yes:
            click.echo("Usa --yes para confirmar el reseteo. Abortando.")
            return
        from ..db import db
        click.echo("Eliminando tablas...")
        db.drop_all()
        click.echo("Recreando tablas...")
        # Importar modelos para registrar metadata
        from ..models.product import Product  # noqa: F401
        from ..models.customer import Customer  # noqa: F401
        from ..models.order import Order  # noqa: F401
        from ..models.order_item import OrderItem  # noqa: F401
        from ..models.price_history import PriceHistory  # noqa: F401
        from ..models.purchase import Purchase  # noqa: F401
        db.create_all()
        click.echo("Base de datos reiniciada.")
