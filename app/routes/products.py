from flask import Blueprint, jsonify, request
from ..models import Product
from .. import db

products_bp = Blueprint("products", __name__)

@products_bp.route("/", methods=["GET"])
def list_products():
    products = Product.query.all()
    return jsonify([{
        "id": p.id, "name": p.name,
        "price": float(p.price), "stock": p.stock
    } for p in products])

@products_bp.route("/<int:pid>", methods=["GET"])
def get_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify({"id": p.id, "name": p.name,
                    "description": p.description,
                    "price": float(p.price), "stock": p.stock})

@products_bp.route("/", methods=["POST"])
def create_product():
    data = request.get_json()
    product = Product(name=data["name"], description=data.get("description"),
                      price=data["price"], stock=data.get("stock", 0))
    db.session.add(product)
    db.session.commit()
    return jsonify({"id": product.id}), 201
