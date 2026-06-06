from flask import Blueprint, jsonify, request
from ..models import Order, OrderItem, Product
from .. import db
from datetime import datetime

orders_bp = Blueprint("orders", __name__)


# ── GET /api/orders/ ──────────────────────────────────────────────────
@orders_bp.route("/", methods=["GET"])
def list_orders():
    """
    List all orders (most recent first).
    Optional query param: ?email=user@example.com to filter by customer.
    """
    email = request.args.get("email")
    query = Order.query.order_by(Order.created_at.desc())

    if email:
        query = query.filter_by(user_email=email.lower().strip())

    orders = query.all()
    return jsonify([_serialize_order(o) for o in orders])


# ── GET /api/orders/<id> ──────────────────────────────────────────────
@orders_bp.route("/<int:order_id>", methods=["GET"])
def get_order(order_id):
    """Fetch a single order with its line items."""
    order = Order.query.get_or_404(order_id)
    return jsonify(_serialize_order(order, include_items=True))


# ── POST /api/orders/ ─────────────────────────────────────────────────
@orders_bp.route("/", methods=["POST"])
def create_order():
    """
    Place a new order and deduct stock atomically.

    Expected body:
    {
        "user_email": "shopper@example.com",
        "items": [
            { "product_id": 1, "quantity": 2 },
            { "product_id": 3, "quantity": 1 }
        ]
    }
    """
    data  = request.get_json(silent=True) or {}
    email = (data.get("user_email") or "").strip().lower()
    items = data.get("items", [])

    # ── Validate input ────────────────────────────────────────────────
    if not email or "@" not in email:
        return jsonify({"error": "A valid user_email is required"}), 400

    if not items or not isinstance(items, list):
        return jsonify({"error": "items must be a non-empty list"}), 400

    # ── Validate each line item & check stock ─────────────────────────
    validated_lines = []
    errors          = []

    for idx, item in enumerate(items):
        product_id = item.get("product_id")
        quantity   = item.get("quantity", 1)

        if not product_id or int(quantity) < 1:
            errors.append(f"Item {idx}: product_id and quantity >= 1 required")
            continue

        product = Product.query.get(int(product_id))
        if not product:
            errors.append(f"Item {idx}: product_id {product_id} not found")
            continue

        if product.stock < int(quantity):
            errors.append(
                f"Item {idx}: '{product.name}' has only {product.stock} in stock "
                f"(requested {quantity})"
            )
            continue

        validated_lines.append({
            "product":  product,
            "quantity": int(quantity),
        })

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    # ── Create order & items inside a transaction ─────────────────────
    try:
        order_total = sum(
            line["product"].price * line["quantity"]
            for line in validated_lines
        )

        order = Order(
            user_email=email,
            total=round(order_total, 2),
            status="confirmed",
        )
        db.session.add(order)
        db.session.flush()          # get order.id without committing yet

        for line in validated_lines:
            product  = line["product"]
            quantity = line["quantity"]

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )
            db.session.add(order_item)

            # Deduct stock atomically
            product.stock -= quantity

        db.session.commit()

    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Could not create order", "detail": str(exc)}), 500

    return jsonify({
        "message":  "Order placed successfully",
        "order_id": order.id,
        "total":    float(order.total),
        "status":   order.status,
    }), 201


# ── PATCH /api/orders/<id>/status ────────────────────────────────────
@orders_bp.route("/<int:order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    """
    Update order status (e.g. confirmed → shipped → delivered).
    Body: { "status": "shipped" }
    """
    VALID_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}

    data   = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()

    if status not in VALID_STATUSES:
        return jsonify({
            "error":   f"Invalid status '{status}'",
            "allowed": sorted(VALID_STATUSES),
        }), 400

    order = Order.query.get_or_404(order_id)

    # Restore stock if cancelling a confirmed/shipped order
    if status == "cancelled" and order.status in ("confirmed", "shipped"):
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity

    order.status = status
    db.session.commit()

    return jsonify({
        "message":  f"Order #{order_id} status updated to '{status}'",
        "order_id": order_id,
        "status":   status,
    })


# ── DELETE /api/orders/<id> ───────────────────────────────────────────
@orders_bp.route("/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    """
    Cancel and delete an order, restoring stock for confirmed orders.
    """
    order = Order.query.get_or_404(order_id)

    if order.status in ("confirmed", "shipped"):
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity

    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": f"Order #{order_id} cancelled and deleted"})


# ── Helper ────────────────────────────────────────────────────────────
def _serialize_order(order: Order, include_items: bool = False) -> dict:
    data = {
        "id":         order.id,
        "user_email": order.user_email,
        "total":      float(order.total),
        "status":     order.status,
        "created_at": order.created_at.isoformat(),
    }
    if include_items:
        data["items"] = [
            {
                "product_id": item.product_id,
                "quantity":   item.quantity,
                "unit_price": float(item.unit_price),
                "line_total": round(float(item.unit_price) * item.quantity, 2),
            }
            for item in order.items
        ]
    return data
