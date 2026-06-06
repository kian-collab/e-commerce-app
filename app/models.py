from . import db
from datetime import datetime

class Product(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Numeric(10, 2), nullable=False)
    stock       = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(200), nullable=False)
    total      = db.Column(db.Numeric(10, 2))
    status     = db.Column(db.String(50), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items      = db.relationship("OrderItem", backref="order", lazy=True)

class OrderItem(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
