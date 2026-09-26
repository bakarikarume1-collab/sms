from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from auth import login_required, get_current_user

from models import (
    db,
    User,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    Notification,
    IntegrationEvent,
    StoreSetting
)

from sms_service import queue_new_order_admin_sms


# =========================================================
# ORDERS BLUEPRINT
# =========================================================

orders = Blueprint("orders", __name__)


# =========================================================
# ALLOWED ORDER STATUSES
# =========================================================

ALLOWED_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "PROCESSING",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "RECEIVED"
}


# =========================================================
# STORE SETTINGS HELPER
# =========================================================

def get_store_setting(key, default=None):

    setting = StoreSetting.query.filter_by(
        key=key
    ).first()

    if not setting:
        return default

    return setting.value


# =========================================================
# ORDER TO DICTIONARY
# =========================================================

def order_to_dict(order):

    return {

        "id": order.id,

        "order_number": order.order_number,

        "status": order.status,

        "subtotal": order.subtotal,

        "delivery_fee": order.delivery_fee,

        "total": order.total,

        "delivery_name": order.delivery_name,

        "delivery_phone": order.delivery_phone,

        "delivery_address": order.delivery_address,

        "delivery_latitude": order.delivery_latitude,

        "delivery_longitude": order.delivery_longitude,

        "delivery_location_shared": bool(
            order.delivery_location_shared
        ),

        "delivery_location_shared_at": (
            order.delivery_location_shared_at.isoformat()
            if order.delivery_location_shared_at
            else None
        ),

        "created_at": (
            order.created_at.isoformat()
            if order.created_at
            else None
        ),

        "updated_at": (
            order.updated_at.isoformat()
            if order.updated_at
            else None
        ),

        "received_at": (
            order.received_at.isoformat()
            if order.received_at
            else None
        ),

        "items": [

            {
                "id": item.id,

                "product_id": item.product_id,

                "product_name": item.product_name,

                "quantity": item.quantity,

                "unit_price": item.unit_price,

                "total": item.total
            }

            for item in order.items
        ]
    }


# =========================================================
# GENERATE ORDER NUMBER
# =========================================================

def generate_order_number():

    today = datetime.utcnow().strftime("%Y%m%d")

    count = Order.query.filter(
        Order.order_number.like(
            f"ORD-{today}-%"
        )
    ).count() + 1

    return f"ORD-{today}-{count:05d}"


# =========================================================
# CREATE ORDER
# =========================================================

@orders.post("/api/orders")
@login_required
def create_order():

    user = get_current_user()

    data = request.get_json(
        silent=True
    ) or {}

    # =====================================================
    # DELIVERY INFORMATION
    # =====================================================

    name = str(
        data.get(
            "delivery_name",
            user.name
        )
    ).strip()

    phone = str(
        data.get(
            "delivery_phone",
            ""
        )
    ).strip()

    address = str(
        data.get(
            "delivery_address",
            ""
        )
    ).strip()

    raw_latitude = data.get(
        "delivery_latitude"
    )

    raw_longitude = data.get(
        "delivery_longitude"
    )

    latitude = None
    longitude = None

    if (
        raw_latitude is not None
        or raw_longitude is not None
    ):

        try:

            latitude = float(
                raw_latitude
            )

            longitude = float(
                raw_longitude
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({

                "success": False,

                "message":
                    "Valid delivery coordinates are required."

            }), 400

        if (
            not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):

            return jsonify({

                "success": False,

                "message":
                    "Delivery coordinates are out of range."

            }), 400

    # =====================================================
    # VALIDATE DELIVERY INFORMATION
    # =====================================================

    if not name or not phone or not address:

        return jsonify({

            "success": False,

            "message": (
                "Delivery name, phone and address "
                "are required."
            )

        }), 400

    # =====================================================
    # CHECK CART
    # =====================================================

    if (
        not user.cart
        or not user.cart.items
    ):

        return jsonify({

            "success": False,

            "message":
                "Your cart is empty."

        }), 400

    # =====================================================
    # CALCULATE ORDER
    # =====================================================

    subtotal = 0

    order_items = []

    # =====================================================
    # VALIDATE PRODUCTS AND STOCK
    # =====================================================

    for item in user.cart.items:

        # -------------------------------------------------
        # PRODUCT MUST EXIST
        # -------------------------------------------------

        if not item.product:

            return jsonify({

                "success": False,

                "message": (
                    "One of the products in your cart "
                    "is no longer available."
                )

            }), 400

        # -------------------------------------------------
        # PRODUCT MUST BE ACTIVE
        # -------------------------------------------------

        if not item.product.is_active:

            return jsonify({

                "success": False,

                "message": (
                    f"{item.product.name} is currently "
                    "unavailable. Please remove it from "
                    "your cart before checkout."
                )

            }), 400

        # -------------------------------------------------
        # QUANTITY MUST BE VALID
        # -------------------------------------------------

        if item.quantity <= 0:

            return jsonify({

                "success": False,

                "message": (
                    f"Invalid quantity for "
                    f"{item.product.name}."
                )

            }), 400

        # -------------------------------------------------
        # CHECK IF PRODUCT IS OUT OF STOCK
        # -------------------------------------------------

        if item.product.stock <= 0:

            return jsonify({

                "success": False,

                "message": (
                    f"{item.product.name} is currently "
                    "out of stock."
                )

            }), 400

        # -------------------------------------------------
        # CHECK REQUESTED QUANTITY AGAINST STOCK
        # -------------------------------------------------

        if item.quantity > item.product.stock:

            return jsonify({

                "success": False,

                "message": (
                    f"Only {item.product.stock} unit(s) "
                    f"of {item.product.name} are available."
                )

            }), 400

        # -------------------------------------------------
        # USE DISCOUNT PRICE WHEN AVAILABLE
        # -------------------------------------------------

        unit_price = (

            item.product.discount_price

            if item.product.discount_price is not None

            else item.product.price
        )

        # -------------------------------------------------
        # CALCULATE ITEM TOTAL
        # -------------------------------------------------

        line_total = (
            unit_price * item.quantity
        )

        subtotal += line_total

        # -------------------------------------------------
        # SAVE ITEM INFORMATION
        # -------------------------------------------------

        order_items.append(
            (
                item,
                unit_price,
                line_total
            )
        )

    # =====================================================
    # LOAD STORE SETTINGS
    # =====================================================

    delivery_fee_setting = get_store_setting(
        "delivery_fee",
        "5000"
    )

    try:

        delivery_fee = float(
            delivery_fee_setting
        )

    except (
        TypeError,
        ValueError
    ):

        delivery_fee = 5000

    # -----------------------------------------------------
    # SAFETY CHECK FOR DELIVERY FEE
    # -----------------------------------------------------

    if delivery_fee < 0:

        delivery_fee = 5000

    # =====================================================
    # MINIMUM ORDER SETTING
    # =====================================================

    minimum_order_setting = get_store_setting(
        "minimum_order",
        "0"
    )

    try:

        minimum_order = float(
            minimum_order_setting
        )

    except (
        TypeError,
        ValueError
    ):

        minimum_order = 0

    # -----------------------------------------------------
    # SAFETY CHECK
    # -----------------------------------------------------

    if minimum_order < 0:

        minimum_order = 0

    # =====================================================
    # CHECK MINIMUM ORDER
    # =====================================================

    if (
        minimum_order > 0
        and subtotal < minimum_order
    ):

        return jsonify({

            "success": False,

            "message": (
                f"Minimum order amount is "
                f"{minimum_order:,.0f} TZS."
            )

        }), 400

    # =====================================================
    # CREATE ORDER
    # =====================================================

    order = Order(

        user_id=user.id,

        order_number=generate_order_number(),

        status="PENDING",

        subtotal=subtotal,

        delivery_fee=delivery_fee,

        total=subtotal + delivery_fee,

        delivery_name=name,

        delivery_phone=phone,

        delivery_address=address,

        delivery_latitude=latitude,

        delivery_longitude=longitude,

        delivery_location_shared=(
            latitude is not None
        ),

        delivery_location_shared_at=(

            datetime.utcnow()

            if latitude is not None

            else None
        )
    )

    db.session.add(order)

    db.session.flush()

    # =====================================================
    # CREATE ORDER ITEMS + REDUCE STOCK
    # =====================================================

    for (
        item,
        unit_price,
        line_total
    ) in order_items:

        # -------------------------------------------------
        # CREATE ORDER ITEM
        # -------------------------------------------------

        db.session.add(

            OrderItem(

                order_id=order.id,

                product_id=item.product_id,

                product_name=item.product.name,

                quantity=item.quantity,

                unit_price=unit_price,

                total=line_total
            )
        )

        # -------------------------------------------------
        # REDUCE PRODUCT STOCK
        # -------------------------------------------------

        item.product.stock -= item.quantity

        # -------------------------------------------------
        # EXTRA SAFETY
        # -------------------------------------------------

        if item.product.stock < 0:

            db.session.rollback()

            return jsonify({

                "success": False,

                "message": (
                    f"Not enough stock for "
                    f"{item.product.name}."
                )

            }), 400

    # =====================================================
    # ORDER STATUS HISTORY
    # =====================================================

    db.session.add(

        OrderStatusHistory(

            order_id=order.id,

            status="PENDING"
        )
    )

    # =====================================================
    # WEBSITE NOTIFICATION
    # =====================================================

    db.session.add(

        Notification(

            user_id=user.id,

            title="Order placed",

            message=(
                f"Your order "
                f"{order.order_number} "
                f"has been placed successfully."
            )
        )
    )

    # =====================================================
    # ADMIN WHATSAPP INTEGRATION EVENT
    # =====================================================

    db.session.add(

        IntegrationEvent(

            event_type="NEW_ORDER_CREATED",

            order_id=order.id,

            payload={

                "order_number":
                    order.order_number,

                "customer_name":
                    user.name,

                "customer_email":
                    user.email,

                "customer_phone":
                    phone,

                "customer_whatsapp":
                    user.whatsapp_number,

                "delivery_address":
                    address,

                "total":
                    order.total,

                "items": [

                    {

                        "name":
                            item.product.name,

                        "quantity":
                            item.quantity,

                        "unit_price":
                            unit_price,

                        "total":
                            line_total
                    }

                    for (
                        item,
                        unit_price,
                        line_total
                    ) in order_items
                ]
            }
        )
    )

    # =====================================================
    # CLEAR CART
    # =====================================================

    for item in list(
        user.cart.items
    ):

        db.session.delete(item)

    # =====================================================
    # COMMIT EVERYTHING
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to place order"
        )

        return jsonify({

            "success": False,

            "message": (
                "Unable to place order. "
                "Please try again."
            )

        }), 500

    # =====================================================
    # NOTIFY ADMIN OF NEW ORDER
    # =====================================================

    try:

        queue_new_order_admin_sms(

            order_id=order.id,

            order_number=order.order_number,

            total=order.total,

            customer_name=(

                order.user.name

                if order.user

                else order.delivery_name
            ),

            customer_phone=order.delivery_phone
        )

    except Exception as exc:

        current_app.logger.warning(

            "Admin new-order SMS was not queued "
            "for order %s: %s",

            order.id,

            exc
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            "Order placed successfully.",

        "order":
            order_to_dict(order),

        "sms_notification": {

            "queued": False,

            "status":
                "WAITING_FOR_ADMIN_STATUS"
        }

    }), 201


# =========================================================
# GET MY ORDERS
# =========================================================

@orders.get("/api/orders")
@login_required
def get_my_orders():

    user = get_current_user()

    user_orders = (

        Order.query

        .filter_by(
            user_id=user.id
        )

        .order_by(
            Order.id.desc()
        )

        .all()
    )

    return jsonify({

        "success": True,

        "orders": [

            order_to_dict(order)

            for order in user_orders
        ]

    })


# =========================================================
# GET SINGLE ORDER
# =========================================================

@orders.get("/api/orders/<int:order_id>")
@login_required
def get_my_order(order_id):

    user = get_current_user()

    order = db.session.get(
        Order,
        order_id
    )

    if not order:

        return jsonify({

            "success": False,

            "message":
                "Order not found."

        }), 404

    # -----------------------------------------------------
    # CUSTOMER CAN ONLY SEE THEIR OWN ORDER
    # -----------------------------------------------------

    if order.user_id != user.id:

        return jsonify({

            "success": False,

            "message":
                "Order not found."

        }), 404

    return jsonify({

        "success": True,

        "order":
            order_to_dict(order)

    })


# =========================================================
# SHARE DELIVERY LOCATION
# =========================================================

@orders.post(
    "/api/orders/<int:order_id>/location"
)
@login_required
def share_delivery_location(order_id):

    user = get_current_user()

    order = db.session.get(
        Order,
        order_id
    )

    if (
        not order
        or order.user_id != user.id
    ):

        return jsonify({

            "success": False,

            "message":
                "Order not found."

        }), 404

    if order.status in {
        "DELIVERED",
        "RECEIVED",
        "CANCELLED",
        "REJECTED"
    }:

        return jsonify({

            "success": False,

            "message": (
                "Location can no longer be "
                "updated for this order."
            )

        }), 400

    data = request.get_json(
        silent=True
    ) or {}

    try:

        latitude = float(
            data.get("latitude")
        )

        longitude = float(
            data.get("longitude")
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({

            "success": False,

            "message":
                "Valid latitude and longitude are required."

        }), 400

    if (
        not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):

        return jsonify({

            "success": False,

            "message":
                "Location coordinates are out of range."

        }), 400

    order.delivery_latitude = latitude

    order.delivery_longitude = longitude

    order.delivery_location_shared = True

    order.delivery_location_shared_at = (
        datetime.utcnow()
    )

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to update delivery location"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to update delivery location."

        }), 500

    return jsonify({

        "success": True,

        "message":
            "Delivery location shared successfully.",

        "order":
            order_to_dict(order)

    })


# =========================================================
# CUSTOMER CONFIRMS ORDER RECEIVED
# =========================================================

@orders.post(
    "/api/orders/<int:order_id>/received"
)
@login_required
def mark_received(order_id):

    user = get_current_user()

    order = db.session.get(
        Order,
        order_id
    )

    # -----------------------------------------------------
    # CHECK ORDER
    # -----------------------------------------------------

    if not order:

        return jsonify({

            "success": False,

            "message":
                "Order not found."

        }), 404

    # -----------------------------------------------------
    # CHECK OWNERSHIP
    # -----------------------------------------------------

    if order.user_id != user.id:

        return jsonify({

            "success": False,

            "message":
                "Order not found."

        }), 404

    # -----------------------------------------------------
    # ORDER MUST BE DELIVERED
    # -----------------------------------------------------

    if order.status != "DELIVERED":

        return jsonify({

            "success": False,

            "message": (
                "Only delivered orders "
                "can be marked as received."
            )

        }), 400

    # -----------------------------------------------------
    # FIND ADMIN
    # -----------------------------------------------------

    admin = User.query.filter_by(
        role="admin"
    ).first()

    if not admin:

        return jsonify({

            "success": False,

            "message":
                "Admin account not found."

        }), 500

    # -----------------------------------------------------
    # CHANGE STATUS
    # -----------------------------------------------------

    order.status = "RECEIVED"

    order.received_at = datetime.utcnow()

    # -----------------------------------------------------
    # STATUS HISTORY
    # -----------------------------------------------------

    db.session.add(

        OrderStatusHistory(

            order_id=order.id,

            status="RECEIVED"
        )
    )

    # =====================================================
    # ADMIN WEBSITE NOTIFICATION
    # =====================================================

    db.session.add(

        Notification(

            user_id=admin.id,

            title="Order received",

            message=(
                f"Customer "
                f"{user.name} "
                f"has confirmed that order "
                f"{order.order_number} "
                f"has been received."
            )
        )
    )

    # =====================================================
    # ADMIN WHATSAPP INTEGRATION EVENT
    # =====================================================

    db.session.add(

        IntegrationEvent(

            event_type="ORDER_RECEIVED",

            order_id=order.id,

            payload={

                "order_number":
                    order.order_number,

                "customer_name":
                    user.name,

                "customer_email":
                    user.email,

                "customer_whatsapp":
                    user.whatsapp_number,

                "delivery_phone":
                    order.delivery_phone,

                "total":
                    order.total,

                "old_status":
                    "DELIVERED",

                "status":
                    "RECEIVED",

                "message": (
                    f"🔔 ORDER RECEIVED\n\n"
                    f"Customer {user.name} "
                    f"has confirmed that order "
                    f"#{order.order_number} "
                    f"has been received."
                )
            }
        )
    )

    # -----------------------------------------------------
    # COMMIT
    # -----------------------------------------------------

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to mark order as received"
        )

        return jsonify({

            "success": False,

            "message": (
                "Unable to update order. "
                "Please try again."
            )

        }), 500

    # -----------------------------------------------------
    # RESPONSE TO CUSTOMER
    # -----------------------------------------------------

    return jsonify({

        "success": True,

        "message":
            "Order received successfully.",

        "order":
            order_to_dict(order)

    })