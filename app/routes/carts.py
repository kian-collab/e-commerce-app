from flask import Blueprint, jsonify, request, session
from ..models import Product
from .. import db

cart_bp = Blueprint("cart", __name__)

# Cart is stored in Flask session as: { "product_id": quantity, ... }
# Session is signed via SECRET_KEY so it's tamper-proof


def _get_cart():
    """Return the raw cart dict from session, initialising if absent."""
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def _cart_with_details(cart: dict):
    """Enrich cart keys (product IDs) with full product data."""
    if not cart:
        return []

    product_ids = [int(pid) for pid in cart.keys()]
    products    = Product.query.filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}

    items = []
    for pid_str, qty in cart.items():
        product = product_map.get(int(pid_str))
        if not product:
            continue          # product was deleted; skip silently
        items.append({
            "product_id":  product.id,
            "name":        product.name,
            "price":       float(product.price),
            "quantity":    qty,
            "line_total":  round(float(product.price) * qty, 2),
            "stock":       product.stock,
        })
    return items


# ── GET /api/cart/ ────────────────────────────────────────────────────
@cart_bp.route("/", methods=["GET"])
def get_cart():
    """Return all cart items with product details and a grand total."""
    cart  = _get_cart()
    items = _cart_with_details(cart)
    total = round(sum(i["line_total"] for i in items), 2)
    return jsonify({"items": items, "total": total, "count": len(items)})


# ── POST /api/cart/ ───────────────────────────────────────────────────
@cart_bp.route("/", methods=["POST"])
def add_to_cart():
    """
    Add or increment a product in the cart.
    Body: { "product_id": int, "quantity": int (default 1) }
    """
    data       = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity   = int(data.get("quantity", 1))

    if not product_id or quantity < 1:
        return jsonify({"error": "product_id and a positive quantity are required"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    cart    = _get_cart()
    key     = str(product_id)
    new_qty = cart.get(key, 0) + quantity

    # Guard against over-ordering
    if new_qty > product.stock:
        return jsonify({
            "error": f"Only {product.stock} units in stock (you already have {cart.get(key, 0)} in cart)"
        }), 409

    cart[key]    = new_qty
    session["cart"] = cart          # mark session as modified
    session.modified = True

    return jsonify({
        "message":    f"Added {quantity}x '{product.name}' to cart",
        "product_id": product.id,
        "quantity":   new_qty,
    }), 201


# ── PATCH /api/cart/<product_id> ──────────────────────────────────────
@cart_bp.route("/<int:product_id>", methods=["PATCH"])
def update_cart_item(product_id):
    """
    Set an exact quantity for a cart item.
    Body: { "quantity": int }
    Set quantity to 0 to remove the item.
    """
    data     = request.get_json(silent=True) or {}
    quantity = data.get("quantity")

    if quantity is None or int(quantity) < 0:
        return jsonify({"error": "quantity must be >= 0"}), 400

    quantity = int(quantity)
    cart     = _get_cart()
    key      = str(product_id)

    if quantity == 0:
        cart.pop(key, None)
        session.modified = True
        return jsonify({"message": "Item removed from cart"})

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if quantity > product.stock:
        return jsonify({"error": f"Only {product.stock} units available"}), 409

    cart[key]        = quantity
    session.modified = True

    return jsonify({
        "message":    f"Cart updated",
        "product_id": product_id,
        "quantity":   quantity,
    })


# ── DELETE /api/cart/<product_id> ─────────────────────────────────────
@cart_bp.route("/<int:product_id>", methods=["DELETE"])
def remove_from_cart(product_id):
    """Remove a specific product from the cart entirely."""
    cart = _get_cart()
    key  = str(product_id)

    if key not in cart:
        return jsonify({"error": "Item not in cart"}), 404

    del cart[key]
    session.modified = True
    return jsonify({"message": "Item removed from cart"})


# ── DELETE /api/cart/ ─────────────────────────────────────────────────
@cart_bp.route("/", methods=["DELETE"])
def clear_cart():
    """Empty the entire cart."""
    session.pop("cart", None)
    return jsonify({"message": "Cart cleared"})
