from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@db:5432/ecommerce"
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

    db.init_app(app)
    migrate.init_app(app, db)

    from .routes.products import products_bp
    from .routes.cart import cart_bp
    from .routes.orders import orders_bp
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(cart_bp,     url_prefix="/api/cart")
    app.register_blueprint(orders_bp,   url_prefix="/api/orders")

    return app
