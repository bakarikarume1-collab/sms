from datetime import datetime
import uuid
import os
import re
from flask import Blueprint, jsonify, request, current_app

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from auth import admin_required, password_policy_error
from models import (
    CartItem,
    OrderItem,
    db,
    User,
    Product,
    ProductImage,
    Category,
    Order,
    OrderStatusHistory,
    Notification,
    IntegrationEvent,
     StoreSetting
)
from sms_service import queue_sms, queue_order_status_customer_sms


# =========================================================
# ADMIN BLUEPRINT
# =========================================================

admin = Blueprint("admin", __name__)


# =========================================================
# PRODUCT IMAGE CONFIGURATION  EXTENSION
# =========================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


def allowed_image(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS

def get_product_upload_folder():

    upload_folder = os.path.join(
        current_app.static_folder,
        "uploads",
        "products"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    return upload_folder


# =========================================================
# VALID ORDER STATUSES
# =========================================================

VALID_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "PROCESSING",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "REJECTED",
    "RECEIVED"
}


# =========================================================
# PRODUCT DICTIONARY
# =========================================================

def admin_product_dict(product):

    images = []

    for image in product.images:

        images.append({
            "id": image.id,
            "image_url": image.image_url,
            "is_primary": bool(image.is_primary)
        })


    primary_image = None


    for image in images:

        if image["is_primary"]:

            primary_image = image["image_url"]

            break


    if not primary_image and images:

        primary_image = images[0]["image_url"]


    return {

        "id": product.id,

        "name": product.name,

        "description":
            product.description or "",

        "price":
            product.price,

        "discount_price":
            product.discount_price,

        "stock":
            product.stock,

        "is_featured":
            bool(product.is_featured),

        "is_active":
            bool(product.is_active),

        "category": (
            {
                "id":
                    product.category.id,

                "name":
                    product.category.name
            }

            if product.category
            else None
        ),

        "images":
            images,

        "primary_image":
            primary_image
    }


# =========================================================
# ORDER DICTIONARY
# =========================================================

def admin_order_dict(order):

    return {

        "id":
            order.id,

        "order_number":
            order.order_number,

        "status":
            order.status,

        "subtotal":
            order.subtotal,

        "delivery_fee":
            order.delivery_fee,

        "total":
            order.total,

        "delivery_name":
            order.delivery_name,

        "delivery_phone":
            order.delivery_phone,

        "delivery_address":
            order.delivery_address,

        "delivery_latitude": order.delivery_latitude,

        "delivery_longitude": order.delivery_longitude,

        "delivery_location_shared": bool(
            order.delivery_location_shared
        ),

        "delivery_location_url": (
            "https://www.google.com/maps?q="
            f"{order.delivery_latitude},{order.delivery_longitude}"
            if order.delivery_location_shared
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

        "customer": {

            "id":
                order.user.id
                if order.user
                else None,

            "name":
                order.user.name
                if order.user
                else None,

            "email":
                order.user.email
                if order.user
                else None,

            "whatsapp_number":
                order.user.whatsapp_number
                if order.user
                else None
        },

        "items": [

            {

                "id":
                    item.id,

                "product_id":
                    item.product_id,

                "product_name":
                    item.product_name,

                "quantity":
                    item.quantity,

                "unit_price":
                    item.unit_price,

                "total":
                    item.total
            }

            for item in order.items
        ]
    }


# =========================================================
# ADMIN DASHBOARD
# =========================================================
@admin.get("/api/admin/dashboard")
@admin_required
def dashboard():

    # =====================================================
    # BASIC STATISTICS
    # =====================================================

    customers_count = User.query.filter_by(
        role="customer"
    ).count()

    products_count = Product.query.count()

    orders_count = Order.query.count()

    pending_count = Order.query.filter_by(
        status="PENDING"
    ).count()

    delivered_count = Order.query.filter_by(
        status="DELIVERED"
    ).count()

    received_count = Order.query.filter_by(
        status="RECEIVED"
    ).count()


    # =====================================================
    # COMPLETED SALES
    # =====================================================
    # DELIVERED + RECEIVED are considered completed sales.
    #
    # An order cannot be both at the same time, so it
    # will not be counted twice.
    # =====================================================

    delivered_revenue = db.session.query(
        db.func.coalesce(
            db.func.sum(Order.total),
            0
        )
    ).filter(
        Order.status.in_([
            "DELIVERED",
            "RECEIVED"
        ])
    ).scalar() or 0


    # =====================================================
    # MONTHLY SALES
    # =====================================================

    monthly_sales = []

    current_year = datetime.utcnow().year

    for month in range(1, 13):

        # -------------------------------------------------
        # Find status history for this month where order
        # became DELIVERED or RECEIVED.
        # -------------------------------------------------

        completed_history = (
            OrderStatusHistory.query
            .filter(
                db.extract(
                    "year",
                    OrderStatusHistory.created_at
                ) == current_year,

                db.extract(
                    "month",
                    OrderStatusHistory.created_at
                ) == month,

                OrderStatusHistory.status.in_([
                    "DELIVERED",
                    "RECEIVED"
                ])
            )
            .all()
        )


        # -------------------------------------------------
        # Calculate sales for this month
        # -------------------------------------------------

        monthly_total = 0

        counted_orders = set()


        for history in completed_history:

            # Prevent the same order from being counted
            # more than once in the same month.
            if history.order_id in counted_orders:
                continue

            order = db.session.get(
                Order,
                history.order_id
            )

            if not order:
                continue


            # Only count orders that are currently
            # DELIVERED or RECEIVED.
            if order.status not in [
                "DELIVERED",
                "RECEIVED"
            ]:
                continue


            monthly_total += order.total

            counted_orders.add(
                history.order_id
            )


        monthly_sales.append({

            "month":
                datetime(
                    current_year,
                    month,
                    1
                ).strftime("%B"),

            "month_number":
                month,

            "sales":
                float(monthly_total)
        })


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "stats": {

            "customers":
                customers_count,

            "products":
                products_count,

            "orders":
                orders_count,

            "pending":
                pending_count,

            "delivered":
                delivered_count,

            "received":
                received_count,

            "delivered_revenue":
                float(delivered_revenue)
        },

        "monthly_sales":
            monthly_sales
    })


# =========================================================
# ADMIN ACCOUNT SETTINGS
# =========================================================
@admin.put("/api/admin/account")
@admin_required
def update_admin_account():


    try:

        from auth import get_current_user

        # -------------------------------------------------
        # GET CURRENT LOGGED-IN ADMIN
        # -------------------------------------------------

        admin_user = get_current_user()

        if not admin_user:

            return jsonify({
                "success": False,
                "message": "Admin session is invalid."
            }), 401


        if admin_user.role != "admin":

            return jsonify({
                "success": False,
                "message": "Admin account required."
            }), 403


        # -------------------------------------------------
        # GET REQUEST DATA
        # -------------------------------------------------

        data = request.get_json(silent=True) or {}


        current_password = str(
            data.get("current_password", "")
        ).strip()


        new_email = str(
            data.get("email", "")
        ).strip().lower()


        new_phone = str(
            data.get("phone", "")
        ).strip()


        new_password = str(
            data.get("new_password", "")
        )


        confirm_password = str(
            data.get("confirm_password", "")
        )


        # -------------------------------------------------
        # CHECK WHAT THE ADMIN WANTS TO CHANGE
        # -------------------------------------------------

        password_change_requested = bool(
            new_password or confirm_password
        )


        # -------------------------------------------------
        # CURRENT PASSWORD
        #
        # Required for ANY sensitive account change.
        # -------------------------------------------------

        if not current_password:

            return jsonify({
                "success": False,
                "message": (
                    "Current password is required "
                    "to update your account."
                )
            }), 400


        if not check_password_hash(
            admin_user.password_hash,
            current_password
        ):

            return jsonify({
                "success": False,
                "message": "Current password is incorrect."
            }), 401


        # -------------------------------------------------
        # EMAIL
        # -------------------------------------------------

        if not new_email:

            return jsonify({
                "success": False,
                "message": "Admin email is required."
            }), 400


        if "@" not in new_email or "." not in new_email:

            return jsonify({
                "success": False,
                "message": "Please enter a valid email address."
            }), 400


        # -------------------------------------------------
        # CHECK EMAIL DUPLICATE
        # -------------------------------------------------

        existing_user = (
            User.query
            .filter(
                User.email == new_email,
                User.id != admin_user.id
            )
            .first()
        )


        if existing_user:

            return jsonify({
                "success": False,
                "message": (
                    "This email is already used "
                    "by another account."
                )
            }), 409


        # -------------------------------------------------
        # PHONE
        # -------------------------------------------------

        if not new_phone:

            return jsonify({
                "success": False,
                "message": "Phone number is required."
            }), 400


        normalized_phone = (
            new_phone
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )


        # -------------------------------------------------
        # NORMALIZE +255
        # -------------------------------------------------

        if normalized_phone.startswith("+255"):

            normalized_phone = normalized_phone[1:]


        elif normalized_phone.startswith("0"):

            normalized_phone = (
                "255" + normalized_phone[1:]
            )


        # -------------------------------------------------
        # VALIDATE TANZANIA PHONE
        # -------------------------------------------------

        if not re.fullmatch(
            r"255\d{9}",
            normalized_phone
        ):

            return jsonify({
                "success": False,
                "message": (
                    "Please enter a valid Tanzania "
                    "phone number. Example: 0712345678"
                )
            }), 400


        # -------------------------------------------------
        # CHECK PHONE DUPLICATE
        # -------------------------------------------------

        existing_phone = (
            User.query
            .filter(
                User.whatsapp_number == normalized_phone,
                User.id != admin_user.id
            )
            .first()
        )


        if existing_phone:

            return jsonify({
                "success": False,
                "message": (
                    "This phone number is already "
                    "used by another account."
                )
            }), 409


        # -------------------------------------------------
        # UPDATE EMAIL
        # -------------------------------------------------

        admin_user.email = new_email


        # -------------------------------------------------
        # UPDATE PHONE
        # -------------------------------------------------

        admin_user.whatsapp_number = normalized_phone


        # -------------------------------------------------
        # PASSWORD UPDATE
        #
        # ONLY RUN IF PASSWORD CHANGE WAS REQUESTED
        # -------------------------------------------------

        if password_change_requested:

            # ---------------------------------------------
            # NEW PASSWORD REQUIRED
            # ---------------------------------------------

            if not new_password:

                return jsonify({
                    "success": False,
                    "message": (
                        "Please enter the new password."
                    )
                }), 400


            # ---------------------------------------------
            # CONFIRM PASSWORD REQUIRED
            # ---------------------------------------------

            if not confirm_password:

                return jsonify({
                    "success": False,
                    "message": (
                        "Please confirm your new password."
                    )
                }), 400


            # ---------------------------------------------
            # PASSWORD MATCH
            # ---------------------------------------------

            if new_password != confirm_password:

                return jsonify({
                    "success": False,
                    "message": (
                        "New passwords do not match."
                    )
                }), 400


            # ---------------------------------------------
            # PASSWORD POLICY
            # ---------------------------------------------

            password_error = password_policy_error(
                new_password
            )


            if password_error:

                return jsonify({
                    "success": False,
                    "message": password_error
                }), 400


            # ---------------------------------------------
            # HASH NEW PASSWORD
            # ---------------------------------------------

            admin_user.password_hash = (
                generate_password_hash(
                    new_password
                )
            )


        # -------------------------------------------------
        # SAVE DATABASE
        # -------------------------------------------------

        db.session.commit()


        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "message": (
                "Admin account updated successfully."
            ),

            "admin": {

                "id": admin_user.id,

                "name": admin_user.name,

                "email": admin_user.email,

                "phone": (
                    admin_user.whatsapp_number
                ),

                "whatsapp_number": (
                    admin_user.whatsapp_number
                ),

                "role": admin_user.role

            }

        }), 200


    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to update admin account."
        )

        return jsonify({

            "success": False,

            "message": (
                "Failed to update admin account."
            )

        }), 500


@admin.get("/api/admin/sales")
@admin_required
def admin_sales():

    try:
        year = request.args.get("year", type=int)

        if not year:
            year = datetime.utcnow().year

        if year < 2000 or year > 2100:
            return jsonify({
                "success": False,
                "message": "Invalid year."
            }), 400

        monthly = []

        total_revenue = 0
        total_orders = 0

        for month in range(1, 13):

            start_date = datetime(year, month, 1)

            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)


            # -------------------------------------------------
            # Find orders that ENTERED DELIVERED during month
            # -------------------------------------------------

            delivered_history = (
                OrderStatusHistory.query
                .filter(
                    OrderStatusHistory.status == "DELIVERED",
                    OrderStatusHistory.created_at >= start_date,
                    OrderStatusHistory.created_at < end_date
                )
                .all()
            )


            # -------------------------------------------------
            # Prevent duplicate counting of same order
            # -------------------------------------------------

            counted_order_ids = set()

            month_orders = []


            for history in delivered_history:

                order_id = history.order_id

                if order_id in counted_order_ids:
                    continue

                counted_order_ids.add(order_id)


                order = Order.query.get(order_id)

                if not order:
                    continue


                # ---------------------------------------------
                # Only count valid completed orders
                # ---------------------------------------------

                if order.status not in [
                    "DELIVERED",
                    "RECEIVED"
                ]:

                    continue


                month_orders.append(order)


            # -------------------------------------------------
            # Calculate month revenue
            # -------------------------------------------------

            month_revenue = sum(
                float(order.total or 0)
                for order in month_orders
            )


            month_order_count = len(month_orders)


            month_average = (
                month_revenue / month_order_count
                if month_order_count > 0
                else 0
            )


            total_revenue += month_revenue
            total_orders += month_order_count


            monthly.append({

                "month":
                    start_date.strftime("%B"),

                "month_number":
                    month,

                "orders":
                    month_order_count,

                "revenue":
                    month_revenue,

                "average_order":
                    month_average
            })


        # -----------------------------------------------------
        # Overall average
        # -----------------------------------------------------

        average_order = (
            total_revenue / total_orders
            if total_orders > 0
            else 0
        )


        active_months = sum(
            1
            for month in monthly
            if month["orders"] > 0
        )


        return jsonify({

            "success": True,

            "year": year,

            "summary": {

                "total_revenue":
                    total_revenue,

                "total_orders":
                    total_orders,

                "average_order":
                    average_order,

                "active_months":
                    active_months
            },

            "monthly_sales":
                monthly
        })


    except Exception as e:

        current_app.logger.exception(
            "Admin sales error"
        )

        return jsonify({

            "success": False,

            "message":
                "Failed to load sales data."
        }), 500

# =========================================================
# GET ALL ORDERS
# =========================================================

@admin.get("/api/admin/orders")
@admin_required
def get_orders():

    orders = Order.query.order_by(
        Order.id.desc()
    ).all()


    return jsonify({

        "success": True,

        "orders": [

            admin_order_dict(order)

            for order in orders
        ]
    })


# =========================================================
# CHANGE ORDER STATUS
# =========================================================
# =========================================================
# CHANGE ORDER STATUS
# =========================================================

@admin.put("/api/admin/orders/<int:order_id>/status")
@admin_required
def change_order_status(order_id):

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
    # GET REQUEST DATA
    # -----------------------------------------------------

    data = request.get_json(
        silent=True
    ) or {}


    new_status = str(
        data.get("status", "")
    ).strip().upper()


    # -----------------------------------------------------
    # VALIDATE STATUS
    # -----------------------------------------------------

    if new_status not in VALID_STATUSES:

        return jsonify({

            "success": False,

            "message":
                "Invalid order status."

        }), 400


    old_status = order.status


    # -----------------------------------------------------
    # PREVENT DUPLICATE STATUS UPDATE
    # -----------------------------------------------------

    if old_status == new_status:

        return jsonify({

            "success": True,

            "message":
                "Order status is already "
                f"{new_status}.",

            "order":
                admin_order_dict(order)

        })


    # =====================================================
    # RESTORE STOCK IF ORDER IS REJECTED
    # =====================================================
    #
    # Example:
    #
    # Product stock = 10
    # Customer orders = 3
    # Stock becomes = 7
    #
    # Admin rejects order
    # Stock becomes = 10 again
    #
    # This happens only when the order is being changed
    # INTO REJECTED.
    #
    # =====================================================

    if new_status == "REJECTED":

        for item in order.items:

            # -------------------------------------------------
            # Find original product
            # -------------------------------------------------

            if item.product_id is None:
                continue


            product = db.session.get(
                Product,
                item.product_id
            )


            # -------------------------------------------------
            # Product may have been deleted
            # -------------------------------------------------

            if not product:
                continue


            # -------------------------------------------------
            # Restore ordered quantity
            # -------------------------------------------------

            product.stock += item.quantity


    # =====================================================
    # UPDATE ORDER STATUS
    # =====================================================

    order.status = new_status


    # -----------------------------------------------------
    # RECEIVED DATE
    # -----------------------------------------------------

    if new_status == "RECEIVED":

        order.received_at = datetime.utcnow()


    # -----------------------------------------------------
    # ORDER STATUS HISTORY
    # -----------------------------------------------------

    db.session.add(

        OrderStatusHistory(

            order_id=order.id,

            status=new_status

        )

    )


    # =====================================================
    # WEBSITE NOTIFICATION
    # =====================================================

    db.session.add(

        Notification(

            user_id=order.user_id,

            title="Order status updated",

            message=(

                f"Your order "

                f"{order.order_number} "

                f"is now "

                f"{new_status.replace('_', ' ')}."

            )

        )

    )


    # =====================================================
    # WHATSAPP ORDER STATUS EVENT
    # =====================================================
    #
    # Every time admin changes order status,
    # create an IntegrationEvent.
    #
    # =====================================================

    customer_whatsapp = None


    if order.user:

        customer_whatsapp = (

            order.user.whatsapp_number

        )


    db.session.add(

        IntegrationEvent(

            event_type=
                "ORDER_STATUS_UPDATED",

            order_id=
                order.id,

            payload={

                "order_number":
                    order.order_number,

                "customer_name": (

                    order.user.name

                    if order.user

                    else order.delivery_name

                ),

                "customer_email": (

                    order.user.email

                    if order.user

                    else None

                ),

                "customer_whatsapp":
                    customer_whatsapp,

                "delivery_phone":
                    order.delivery_phone,

                "total":
                    order.total,

                "old_status":
                    old_status,

                "status":
                    new_status,

                "message": (

                    f"Your order "

                    f"{order.order_number} "

                    f"is now "

                    f"{new_status.replace('_', ' ')}."

                )

            }

        )

    )


    # =====================================================
    # SAVE EVERYTHING
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(

            "Unable to update order status"

        )

        return jsonify({

            "success": False,

            "message":
                "Unable to update order status."

        }), 500

    # =====================================================
    # CUSTOMER SMS NOTIFICATION
    # =====================================================

    try:
        customer_phone = order.delivery_phone
        if not customer_phone and order.user:
            customer_phone = order.user.whatsapp_number

        queue_order_status_customer_sms(
            order_id=order.id,
            order_number=order.order_number,
            phone=customer_phone,
            new_status=new_status,
            customer_name=(
                order.user.name
                if order.user
                else order.delivery_name
            ),
        )
    except Exception as exc:
        current_app.logger.warning(
            "Customer status SMS was not queued for order %s: %s",
            order.id,
            exc,
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":

            f"Order status changed from "

            f"{old_status} to "

            f"{new_status}.",

        "order":

            admin_order_dict(order)

    }), 200


@admin.get("/api/admin/settings")
@admin_required
def get_admin_settings():

    try:

        settings = StoreSetting.query.all()

        data = {
            setting.key: setting.value
            for setting in settings
        }

        return jsonify({
            "success": True,
            "settings": data
        })

    except Exception:

        current_app.logger.exception(
            "Failed to load admin settings"
        )

        return jsonify({
            "success": False,
            "message": "Failed to load settings."
        }), 500

@admin.put("/api/admin/settings")
@admin_required
def update_admin_settings():

    try:

        data = request.get_json(silent=True) or {}

        allowed_settings = {
            "store_name",
            "store_phone",
            "store_email",
            "store_address",
            "delivery_fee",
            "minimum_order",
            "maintenance_mode",
            "whatsapp_notifications",
            "sms_notifications",
            "email_notifications"
        }

        boolean_settings = {
            "maintenance_mode",
            "whatsapp_notifications",
            "sms_notifications",
            "email_notifications"
        }

        for key, value in data.items():

            if key not in allowed_settings:
                continue

            # Normalize boolean settings
            if key in boolean_settings:
                if isinstance(value, bool):
                    value = "true" if value else "false"
                else:
                    value = str(value).strip().lower()

                    if value in {"1", "true", "yes", "on"}:
                        value = "true"
                    else:
                        value = "false"

            setting = (
                StoreSetting.query
                .filter_by(key=key)
                .first()
            )

            if not setting:

                setting = StoreSetting(
                    key=key,
                    value=str(value)
                )

                db.session.add(setting)

            else:

                setting.value = str(value)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Settings updated successfully."
        })

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to update admin settings"
        )

        return jsonify({
            "success": False,
            "message": "Failed to update settings."
        }), 500

# =========================================================
# GET CUSTOMERS
# =========================================================

@admin.get("/api/admin/customers")
@admin_required
def get_customers():

    customers = User.query.filter_by(
        role="customer"
    ).order_by(
        User.id.desc()
    ).all()


    return jsonify({

        "success": True,

        "customers": [

            {

                "id":
                    customer.id,

                "name":
                    customer.name,

                "email":
                    customer.email,

                "whatsapp_number":
                    customer.whatsapp_number,

                "is_active":
                    customer.is_active,

                "created_at": (
                    customer.created_at.isoformat()
                    if customer.created_at
                    else None
                )
            }

            for customer in customers
        ]
    })


# =========================================================
# GET PRODUCTS
# =========================================================

@admin.get("/api/admin/products")
@admin_required
def get_products():

    products = Product.query.order_by(
        Product.id.desc()
    ).all()


    return jsonify({

        "success": True,

        "products": [

            admin_product_dict(product)

            for product in products
        ]
    })


# =========================================================
# CREATE PRODUCT
# =========================================================
@admin.post("/api/admin/products")
@admin_required
def create_product():

    # =====================================================
    # FORM DATA
    # =====================================================

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    category_id = request.form.get(
        "category_id"
    )

    price = request.form.get(
        "price"
    )

    discount_price = request.form.get(
        "discount_price"
    )

    stock = request.form.get(
        "stock",
        "0"
    )

    is_featured = request.form.get(
        "is_featured"
    )


    # =====================================================
    # BASIC VALIDATION
    # =====================================================

    if not name:

        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400


    if not category_id:

        return jsonify({
            "success": False,
            "message": "Product category is required."
        }), 400


    if price in (None, ""):

        return jsonify({
            "success": False,
            "message": "Product price is required."
        }), 400


    # =====================================================
    # CATEGORY
    # =====================================================

    try:

        category_id = int(
            category_id
        )

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid category."
        }), 400


    category = db.session.get(
        Category,
        category_id
    )


    if not category:

        return jsonify({
            "success": False,
            "message": "Selected category does not exist."
        }), 400


    # =====================================================
    # PRICE
    # =====================================================

    try:

        price = float(price)

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid product price."
        }), 400


    if price <= 0:

        return jsonify({
            "success": False,
            "message":
                "Product price must be greater than 0."
        }), 400


    # =====================================================
    # DISCOUNT PRICE
    # =====================================================

    if discount_price in (None, ""):

        discount_price = None

    else:

        try:

            discount_price = float(
                discount_price
            )

        except (ValueError, TypeError):

            return jsonify({
                "success": False,
                "message": "Invalid discount price."
            }), 400


        if discount_price < 0:

            return jsonify({
                "success": False,
                "message":
                    "Discount price cannot be negative."
            }), 400


        if discount_price >= price:

            return jsonify({
                "success": False,
                "message":
                    "Discount price must be lower than the original price."
            }), 400


    # =====================================================
    # STOCK
    # =====================================================

    try:

        stock = int(stock)

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message":
                "Invalid stock quantity."
        }), 400


    if stock < 0:

        return jsonify({
            "success": False,
            "message":
                "Stock cannot be negative."
        }), 400


    # =====================================================
    # FEATURED
    # =====================================================

    is_featured = (
        str(is_featured).lower()
        in {"true", "1", "yes", "on"}
    )


    # =====================================================
    # IMAGE
    # =====================================================

    image_file = request.files.get(
        "image"
    )


    if image_file:

        if not image_file.filename:

            image_file = None


    if image_file:

        if not allowed_image(
            image_file.filename
        ):

            return jsonify({
                "success": False,
                "message":
                    "Invalid image format. "
                    "Use JPG, JPEG, PNG or WEBP."
            }), 400


    # =====================================================
    # CREATE PRODUCT
    # =====================================================

    product = Product(

        name=name,

        description=description,

        price=price,

        discount_price=discount_price,

        stock=stock,

        is_featured=is_featured,

        category_id=category_id

    )


    db.session.add(product)

    db.session.flush()


    # =====================================================
    # SAVE IMAGE
    # =====================================================

    if image_file:

        original_filename = secure_filename(
            image_file.filename
        )


        extension = original_filename.rsplit(
            ".",
            1
        )[1].lower()


        unique_filename = (
            f"{uuid.uuid4().hex}.{extension}"
        )


        upload_folder = (
            get_product_upload_folder()
        )


        image_path = os.path.join(
            upload_folder,
            unique_filename
        )


        image_file.save(
            image_path
        )


        image_url = (
            f"/static/uploads/products/"
            f"{unique_filename}"
        )


        product_image = ProductImage(

            product_id=product.id,

            image_url=image_url,

            is_primary=True

        )


        db.session.add(
            product_image
        )


    # =====================================================
    # COMMIT
    # =====================================================

    db.session.commit()


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            "Product created successfully.",

        "product":
            admin_product_dict(product)

    }), 201
# =========================================================
# UPDATE PRODUCT
# =========================================================

@admin.put("/api/admin/products/<int:product_id>")
@admin_required
def update_product(product_id):

    

    product = db.session.get(
        Product,
        product_id
    )

    if not product:

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404



    # If request is multipart/form-data
    # data comes from request.form
    if request.content_type and request.content_type.startswith(
        "multipart/form-data"
    ):

        data = request.form

    else:

        # Normal JSON request
        data = request.get_json(
            silent=True
        ) or {}



    if "name" in data:

        name = str(
            data["name"]
        ).strip()

        if not name:

            return jsonify({
                "success": False,
                "message": "Product name is required."
            }), 400

        product.name = name


    if "description" in data:

        product.description = str(
            data["description"]
        ).strip()


    if "price" in data:

        try:

            price = float(
                data["price"]
            )

            if price < 0:

                return jsonify({
                    "success": False,
                    "message": "Price cannot be negative."
                }), 400

            product.price = price

        except (
            ValueError,
            TypeError
        ):

            return jsonify({
                "success": False,
                "message": "Invalid price."
            }), 400


    if "discount_price" in data:

        try:

            value = data["discount_price"]

            if value in (None, ""):

                product.discount_price = None

            else:

                discount_price = float(
                    value
                )

                if discount_price < 0:

                    return jsonify({
                        "success": False,
                        "message":
                            "Discount price cannot be negative."
                    }), 400

                product.discount_price = discount_price

        except (
            ValueError,
            TypeError
        ):

            return jsonify({
                "success": False,
                "message": "Invalid discount price."
            }), 400


    if "stock" in data:

        try:

            stock = int(
                data["stock"]
            )

            if stock < 0:

                return jsonify({
                    "success": False,
                    "message":
                        "Stock cannot be negative."
                }), 400

            product.stock = stock

        except (
            ValueError,
            TypeError
        ):

            return jsonify({
                "success": False,
                "message": "Invalid stock."
            }), 400



    if "is_featured" in data:

        value = data["is_featured"]

        if isinstance(value, str):

            product.is_featured = (
                value.lower()
                in (
                    "true",
                    "1",
                    "yes",
                    "on"
                )
            )

        else:

            product.is_featured = bool(
                value
            )



    if "category_id" in data:

        category_id = data["category_id"]

        if category_id in (None, ""):

            product.category_id = None

        else:

            try:

                category_id = int(
                    category_id
                )

                category = db.session.get(
                    Category,
                    category_id
                )

                if not category:

                    return jsonify({
                        "success": False,
                        "message":
                            "Category not found."
                    }), 404

                product.category_id = category_id

            except (
                ValueError,
                TypeError
            ):

                return jsonify({
                    "success": False,
                    "message":
                        "Invalid category."
                }), 400



    image_file = request.files.get(
        "image"
    )


    if image_file and image_file.filename:

        if not allowed_image(
            image_file.filename
        ):

            return jsonify({
                "success": False,
                "message":
                    "Invalid image format. "
                    "Allowed: JPG, JPEG, PNG, WEBP."
            }), 400


        # -------------------------------------------------
        # Save new image
        # -------------------------------------------------

        original_filename = secure_filename(
            image_file.filename
        )

        extension = (
            original_filename
            .rsplit(".", 1)[1]
            .lower()
        )

        unique_filename = (
            f"{uuid.uuid4().hex}.{extension}"
        )


        upload_folder = (
            get_product_upload_folder()
        )


        image_path = os.path.join(
            upload_folder,
            unique_filename
        )


        image_file.save(
            image_path
        )


        image_url = (
            f"/static/uploads/products/"
            f"{unique_filename}"
        )



        old_primary_image = None

        for image in product.images:

            if image.is_primary:

                old_primary_image = image

                break


        if old_primary_image:

            old_primary_image.is_primary = False


        new_product_image = ProductImage(
            product_id=product.id,
            image_url=image_url,
            is_primary=True
        )


        db.session.add(
            new_product_image
        )


        # -------------------------------------------------
        # Delete old image file
        # -------------------------------------------------

        if old_primary_image:

            old_image_url = (
                old_primary_image.image_url
            )

            if old_image_url.startswith(
                "/static/uploads/products/"
            ):

                old_filename = (
                    old_image_url
                    .replace(
                        "/static/uploads/products/",
                        "",
                        1
                    )
                )

                old_file_path = os.path.join(
                    upload_folder,
                    old_filename
                )

                if os.path.isfile(
                    old_file_path
                ):

                    try:

                        os.remove(
                            old_file_path
                        )

                    except OSError:

                        pass

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to update product"
        )

        return jsonify({
            "success": False,
            "message":
                "Failed to update product."
        }), 500


    return jsonify({

        "success": True,

        "message":
            "Product updated successfully.",

        "product":
            admin_product_dict(product)

    })



def get_store_setting(key, default=None):

    setting = (
        StoreSetting.query
        .filter_by(key=key)
        .first()
    )

    if not setting:
        return default

    return setting.value




# =========================================================
# CHANGE PRODUCT ACTIVE STATUS
# =========================================================
#
# ACTIVE:
#   Product inaonekana kwa customers
#   Product inaweza kuongezwa kwenye cart
#   Product inaweza kuagizwa
#
# INACTIVE:
#   Product haionekani kwa customers
#   Haiwezi kuongezwa kwenye cart
#   Haiwezi ku-checkout
#   Order history ya zamani inabaki salama
#
# =========================================================

@admin.put("/api/admin/products/<int:product_id>/status")
@admin_required
def change_product_status(product_id):

    # =====================================================
    # FIND PRODUCT
    # =====================================================

    product = db.session.get(
        Product,
        product_id
    )

    if not product:

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404


    # =====================================================
    # GET REQUEST DATA
    # =====================================================

    data = request.get_json(
        silent=True
    ) or {}


    is_active = data.get(
        "is_active"
    )


    # =====================================================
    # VALIDATE is_active
    # =====================================================

    if not isinstance(
        is_active,
        bool
    ):

        return jsonify({
            "success": False,
            "message":
                "is_active must be true or false."
        }), 400


    # =====================================================
    # CHECK CURRENT STATUS
    # =====================================================

    if product.is_active == is_active:

        status_text = (
            "active"
            if is_active
            else "inactive"
        )

        return jsonify({

            "success": True,

            "message":
                f"Product is already {status_text}.",

            "product":
                admin_product_dict(product)

        }), 200


    # =====================================================
    # UPDATE STATUS
    # =====================================================

    product.is_active = is_active


    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to change product status"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to change product status."

        }), 500


    # =====================================================
    # RESPONSE MESSAGE
    # =====================================================

    if is_active:

        message = (
            "Product activated successfully."
        )

    else:

        message = (
            "Product deactivated successfully."
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            message,

        "product":
            admin_product_dict(product)

    }), 200

# =========================================================
# DELETE PRODUCT
# =========================================================

@admin.delete("/api/admin/products/<int:product_id>")
@admin_required
def delete_product(product_id):

    # =====================================================
    # FIND PRODUCT
    # =====================================================

    product = db.session.get(
        Product,
        product_id
    )

    if not product:

        return jsonify({
            "success": False,
            "message": "Product not found."
        }), 404


    # =====================================================
    # CHECK PRODUCT IN CUSTOMER CART
    # =====================================================

    cart_item = CartItem.query.filter_by(
        product_id=product.id
    ).first()

    if cart_item:

        return jsonify({
            "success": False,
            "message": (
                "This product cannot be deleted because "
                "it is currently in a customer's cart."
            )
        }), 400


    # =====================================================
    # CHECK PRODUCT IN ORDER HISTORY
    # =====================================================

    order_item = OrderItem.query.filter_by(
        product_id=product.id
    ).first()

    if order_item:

        return jsonify({
            "success": False,
            "message": (
                "This product cannot be deleted because "
                "it is already part of an order history."
            )
        }), 400


    # =====================================================
    # COLLECT PRODUCT IMAGE FILES
    # =====================================================

    image_files = []

    upload_folder = get_product_upload_folder()

    for image in product.images:

        if not image.image_url:
            continue

        if image.image_url.startswith(
            "/static/uploads/products/"
        ):

            filename = image.image_url.replace(
                "/static/uploads/products/",
                "",
                1
            )

            image_path = os.path.join(
                upload_folder,
                filename
            )

            image_files.append(
                image_path
            )


    # =====================================================
    # DELETE PRODUCT FROM DATABASE
    # =====================================================

    try:

        db.session.delete(
            product
        )

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to delete product"
        )

        return jsonify({
            "success": False,
            "message":
                "Unable to delete product."
        }), 500


    # =====================================================
    # DELETE IMAGE FILES FROM DISK
    # =====================================================

    for image_path in image_files:

        if os.path.isfile(
            image_path
        ):

            try:

                os.remove(
                    image_path
                )

            except OSError:

                current_app.logger.warning(
                    "Could not delete image file: %s",
                    image_path
                )


    # =====================================================
    # SUCCESS
    # =====================================================

    return jsonify({
        "success": True,
        "message":
            "Product deleted successfully."
    }), 200


# =========================================================
# CREATE CATEGORY
# =========================================================

@admin.post("/api/admin/categories")
@admin_required
def create_category():

    data = request.get_json(
        silent=True
    ) or {}


    name = str(
        data.get("name", "")
    ).strip()


    if not name:

        return jsonify({

            "success": False,

            "message":
                "Category name is required."

        }), 400


    existing = Category.query.filter_by(
        name=name
    ).first()


    if existing:

        return jsonify({

            "success": False,

            "message":
                "Category already exists."

        }), 409


    category = Category(
        name=name
    )


    db.session.add(category)

    db.session.commit()


    return jsonify({

        "success": True,

        "message":
            "Category created successfully.",

        "category": {

            "id":
                category.id,

            "name":
                category.name
        }

    }), 201