import os
from datetime import timedelta

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text

from auth import get_current_user
from models import db, Category, Product, StoreSetting, User
from werkzeug.security import generate_password_hash


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# INSTANCE FOLDER
# =========================================================

instance_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "instance"
)

os.makedirs(instance_path, exist_ok=True)


# =========================================================
# DATABASE PATH
# =========================================================

database_path = os.path.join(
    instance_path,
    "store.db"
)


# =========================================================
# DATABASE URL
# =========================================================

database_url = os.environ.get("DATABASE_URL")

if database_url:

    # Support older PostgreSQL URL format
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

else:

    # Local development uses SQLite
    database_url = (
        "sqlite:///"
        + database_path.replace("\\", "/")
    )


# =========================================================
# CONFIGURATION
# =========================================================

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY"
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": 30,
    "connect_args": {
        "connect_timeout": 10
    }
}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    days=7
)

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE",
    "0",
) == "1"


# =========================================================
# INITIALIZE DATABASE
# =========================================================

db.init_app(app)


# =========================================================
# STORE SETTINGS
# =========================================================

def get_store_setting(key, default=None):

    setting = StoreSetting.query.filter_by(
        key=key
    ).first()

    if not setting:
        return default

    return setting.value


# =========================================================
# STORE SETTINGS CONTEXT
# =========================================================

@app.context_processor
def inject_store_settings():

    return {
        "store_name": get_store_setting(
            "store_name",
            "KarumeStore"
        )
    }


# =========================================================
# API ORIGIN PROTECTION
# =========================================================

@app.before_request
def protect_api_origin():

    if request.method not in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE"
    }:
        return None

    if not request.path.startswith("/api/"):
        return None

    origin = request.headers.get("Origin")

    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify({
            "success": False,
            "message": "Cross-origin request rejected.",
        }), 403

    return None


# =========================================================
# BLUEPRINTS
# =========================================================

from auth import auth
from products import products
from cart import cart
from orders import orders
from admin import admin
from notifications import notifications
from integration import integration
from sms_admin import sms_admin
from pages import pages


app.register_blueprint(auth)
app.register_blueprint(products)
app.register_blueprint(cart)
app.register_blueprint(orders)
app.register_blueprint(admin)
app.register_blueprint(notifications)
app.register_blueprint(integration)
app.register_blueprint(sms_admin)
app.register_blueprint(pages)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "message": "KarumeStore API is running."
    })


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(400)
def bad_request(error):

    return jsonify({
        "success": False,
        "message": "Bad request.",
    }), 400


@app.errorhandler(401)
def unauthorized(error):

    return jsonify({
        "success": False,
        "message": "Authentication required.",
    }), 401


@app.errorhandler(403)
def forbidden(error):

    return jsonify({
        "success": False,
        "message": "Access denied.",
    }), 403


@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "success": False,
            "message": "Resource not found.",
        }), 404

    return error


@app.errorhandler(429)
def too_many_requests(error):

    return jsonify({
        "success": False,
        "message": "Too many requests.",
    }), 429


# =========================================================
# CURRENT USER CONTEXT
# =========================================================

@app.context_processor
def inject_current_user():

    return {
        "user": get_current_user()
    }


# =========================================================
# SERVER ERROR
# =========================================================

@app.errorhandler(500)
def server_error(error):

    return jsonify({
        "success": False,
        "message": "Internal server error.",
    }), 500


# =========================================================
# DATABASE MIGRATION
# =========================================================

def migrate_database():

    inspector = inspect(db.engine)

    tables = inspector.get_table_names()


    # -----------------------------------------------------
    # USERS TABLE
    # -----------------------------------------------------

    if "users" not in tables:

        print(
            "Users table does not exist yet."
        )

        return


    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }


    # -----------------------------------------------------
    # ADD WHATSAPP NUMBER
    # -----------------------------------------------------

    if "whatsapp_number" not in columns:

        print(
            "Adding whatsapp_number column..."
        )

        db.session.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN whatsapp_number VARCHAR(30)"
            )
        )

        db.session.commit()

        print(
            "whatsapp_number added successfully."
        )


    # -----------------------------------------------------
    # ORDERS TABLE COLUMNS
    # -----------------------------------------------------

    order_columns = {

        column["name"]

        for column in inspector.get_columns("orders")

    } if "orders" in tables else set()


    # -----------------------------------------------------
    # DELIVERY LOCATION COLUMNS
    # -----------------------------------------------------

    location_columns = {

        "delivery_latitude":
            "DOUBLE PRECISION",

        "delivery_longitude":
            "DOUBLE PRECISION",

        "delivery_location_shared":
            "BOOLEAN NOT NULL DEFAULT FALSE",

        "delivery_location_shared_at":
            "TIMESTAMP",

    }


    # -----------------------------------------------------
    # ADD MISSING ORDER COLUMNS
    # -----------------------------------------------------

    for column_name, column_type in location_columns.items():

        if column_name not in order_columns:

            print(
                f"Adding {column_name} column..."
            )

            db.session.execute(
                text(
                    f"ALTER TABLE orders "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )

            db.session.commit()

            print(
                f"{column_name} added successfully."
            )


# =========================================================
# DEFAULT CATEGORIES
# =========================================================

def seed_default_categories():

    """
    Create default categories if they do not exist.

    This function DOES NOT create products.

    Existing categories are preserved.
    """

    default_categories = [

        "Clothes",

        "Shoes",

        "Fridges",

        "Electronics",

        "Bags",

        "Watches",

        "Accessories",

        "Home Appliances",

    ]


    print(
        "Checking default categories..."
    )


    created_count = 0


    for category_name in default_categories:

        existing_category = (
            Category.query
            .filter_by(
                name=category_name
            )
            .first()
        )


        if existing_category:

            print(
                f"Category already exists: "
                f"{category_name}"
            )

            continue


        category = Category(
            name=category_name
        )


        db.session.add(
            category
        )


        created_count += 1


    # -----------------------------------------------------
    # SAVE NEW CATEGORIES
    # -----------------------------------------------------

    if created_count > 0:

        db.session.commit()

        print(
            f"Created {created_count} "
            f"default categories."
        )

    else:

        print(
            "All default categories "
            "already exist."
        )


# =========================================================
# DEFAULT ADMIN
# =========================================================

def seed_default_admin():

    """
    Create the admin account if it does not already exist.

    Admin credentials are read from environment variables:

        ADMIN_EMAIL
        ADMIN_PASSWORD

    Existing users are never modified.
    Existing admin passwords are never overwritten.
    """

    admin_email = os.environ.get(
        "ADMIN_EMAIL"
    )

    admin_password = os.environ.get(
        "ADMIN_PASSWORD"
    )

    # -----------------------------------------------------
    # CHECK ENVIRONMENT VARIABLES
    # -----------------------------------------------------

    if not admin_email or not admin_password:

        print(
            "ADMIN_EMAIL or ADMIN_PASSWORD "
            "is not configured."
        )

        print(
            "Admin creation skipped."
        )

        return

    admin_email = admin_email.strip().lower()

    # -----------------------------------------------------
    # CHECK IF EMAIL ALREADY EXISTS
    # -----------------------------------------------------

    existing_user = User.query.filter_by(
        email=admin_email
    ).first()

    if existing_user:

        if existing_user.role == "admin":

            print(
                f"Admin already exists: "
                f"{admin_email}"
            )

        else:

            print(
                f"User already exists with email "
                f"{admin_email}, but is not an admin."
            )

        return

    # -----------------------------------------------------
    # CREATE ADMIN
    # -----------------------------------------------------

    admin = User(
        name="Administrator",
        email=admin_email,
        password_hash=generate_password_hash(
            admin_password
        ),
        whatsapp_number=None,
        role="admin",
        is_active=True
    )

    db.session.add(admin)

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    try:

        db.session.commit()

        print(
            "========================================"
        )

        print(
            "DEFAULT ADMIN CREATED"
        )

        print(
            f"Admin email: {admin_email}"
        )

        print(
            "Admin password: configured from "
            "ADMIN_PASSWORD"
        )

        print(
            "========================================"
        )

    except Exception as error:

        db.session.rollback()

        print(
            "========================================"
        )

        print(
            "ADMIN CREATION FAILED"
        )

        print(error)

        print(
            "========================================"
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def create_database():

    with app.app_context():

        print("========================================")

        print(
            "DATABASE INITIALIZATION"
        )

        print("========================================")


        # -------------------------------------------------
        # DATABASE INFORMATION
        # -------------------------------------------------

        print(
            "Database:",
            str(
                db.engine.url.database
            )
        )

        print(
            "Engine:",
            db.engine.url.drivername
        )


        # -------------------------------------------------
        # CREATE TABLES
        # -------------------------------------------------

        print(
            "Creating missing tables..."
        )

        db.create_all()

        print(
            "Database tables created/verified."
        )


        # -------------------------------------------------
        # DATABASE MIGRATIONS
        # -------------------------------------------------

        print(
            "Running database migrations..."
        )

        migrate_database()


        # -------------------------------------------------
        # DEFAULT CATEGORIES
        # -------------------------------------------------

        print(
            "Initializing default categories..."
        )

        seed_default_categories()


        # -------------------------------------------------
        # DEFAULT ADMIN
        # -------------------------------------------------

        print(
            "Initializing default admin..."
        )

        seed_default_admin()


        # -------------------------------------------------
        # PRODUCTS
        # -------------------------------------------------

        print(
            "Product seeding skipped."
        )


        # -------------------------------------------------
        # COMPLETE
        # -------------------------------------------------

        print(
            "Database initialization completed."
        )

        print(
            "========================================"
        )

# =========================================================
# DEBUG DATABASE ROUTE
# =========================================================

@app.route("/api/debug/database")
def debug_database():

    with app.app_context():

        categories = Category.query.order_by(
            Category.id.asc()
        ).all()


        products_list = Product.query.order_by(
            Product.id.asc()
        ).all()


        return jsonify({

            "success": True,

            "database":
                str(
                    db.engine.url.database
                ),

            "driver":
                db.engine.url.drivername,

            "categories_count":
                len(categories),

            "products_count":
                len(products_list),

            "categories": [

                {
                    "id":
                        category.id,

                    "name":
                        category.name
                }

                for category in categories
            ],

            "products": [

                {

                    "id":
                        product.id,

                    "name":
                        product.name,

                    "price":
                        product.price,

                    "category_id":
                        product.category_id,

                    "category":
                        (
                            product.category.name
                            if product.category
                            else None
                        )

                }

                for product in products_list
            ]

        })


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

try:

    create_database()

except Exception as error:

    print("========================================")

    print(
        "DATABASE INITIALIZATION FAILED"
    )

    print("========================================")

    print(error)

    print("========================================")


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
