from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# =========================================================
# USER
# =========================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # WhatsApp number used for customer notifications
    whatsapp_number = db.Column(
        db.String(30),
        nullable=True
    )

    role = db.Column(
        db.String(20),
        default="customer",
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


#=======================================
#PASSWORD RESET PATH
#=======================================

# PASSWORD RESET
class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    otp_hash = db.Column(
        db.String(255),
        nullable=False
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    attempts = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    used = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "password_resets",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

# =========================================================
# CATEGORY
# =========================================================

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    products = db.relationship(
        "Product",
        backref="category",
        lazy=True
    )


# =========================================================
# PRODUCT
# =========================================================

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id")
    )

    

# =========================================================
# PRODUCT IMAGE
# =========================================================

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    image_url = db.Column(
        db.String(500),
        nullable=False
    )

    is_primary = db.Column(
        db.Boolean,
        default=False
    )

    product = db.relationship(
        "Product",
        backref=db.backref(
            "images",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )


# =========================================================
# CART
# =========================================================

class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "cart",
            uselist=False
        )
    )


# =========================================================
# CART ITEM
# =========================================================

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    cart_id = db.Column(
        db.Integer,
        db.ForeignKey("carts.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    cart = db.relationship(
        "Cart",
        backref=db.backref(
            "items",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    product = db.relationship("Product")


# =========================================================
# ORDER
# =========================================================

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    order_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="PENDING",
        nullable=False
    )

    subtotal = db.Column(
        db.Float,
        nullable=False
    )

    delivery_fee = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    total = db.Column(
        db.Float,
        nullable=False
    )

    delivery_name = db.Column(
        db.String(100),
        nullable=False
    )

    delivery_phone = db.Column(
        db.String(50),
        nullable=False
    )

    delivery_address = db.Column(
        db.Text,
        nullable=False
    )

    delivery_latitude = db.Column(
        db.Float,
        nullable=True
    )

    delivery_longitude = db.Column(
        db.Float,
        nullable=True
    )

    delivery_location_shared = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    delivery_location_shared_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    received_at = db.Column(
        db.DateTime
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "orders",
            lazy=True
        )
    )


# =========================================================
# ORDER ITEM
# =========================================================

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id")
    )

    product_name = db.Column(
        db.String(200),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Float,
        nullable=False
    )

    total = db.Column(
        db.Float,
        nullable=False
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "items",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )


# =========================================================
# ORDER STATUS HISTORY
# =========================================================

class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.ForeignKey("orders.id"),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "status_history",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )


# =========================================================
# WEBSITE NOTIFICATION
# =========================================================

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "notifications",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )


# =========================================================
# INTEGRATION EVENT
# =========================================================

class IntegrationEvent(db.Model):
    __tablename__ = "integration_events"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_type = db.Column(
        db.String(80),
        nullable=False,
        index=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        index=True
    )

    payload_json = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True
    )

    @property
    def payload(self):
        try:
            return json.loads(self.payload_json)
        except (TypeError, json.JSONDecodeError):
            return {}

    @payload.setter
    def payload(self, value):
        self.payload_json = json.dumps(
            value,
            ensure_ascii=False
        )


class StoreSetting(db.Model):
    __tablename__ = "store_settings"

    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    value = db.Column(
        db.Text,
        nullable=True
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<StoreSetting {self.key}>"  