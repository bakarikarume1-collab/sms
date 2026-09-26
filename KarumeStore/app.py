import os
from datetime import timedelta
from auth import get_current_user

from flask import Flask, jsonify, request
from sqlalchemy import inspect, text

from models import db, Category, Product, StoreSetting


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


database_url = os.environ.get("DATABASE_URL")

if not database_url:
    database_url = "sqlite:///" + database_path.replace("\\", "/")

# =========================================================
# CONFIGURATION
# =========================================================

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

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

# =========================================================
# INITIALIZE DATABASE
# =========================================================

db.init_app(app)


def get_store_setting(key, default=None):
    setting = StoreSetting.query.filter_by(
        key=key
    ).first()

    if not setting:
        return default

    return setting.value


@app.context_processor
def inject_store_settings():
    return {
        "store_name": get_store_setting(
            "store_name",
            "KarumeStore"
        )
    }


@app.before_request
def protect_api_origin():

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
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

@app.context_processor
def inject_current_user():
    return {
        "user": get_current_user()
    }


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

        print("Users table does not exist yet.")

        return

    columns = {
        column["name"]
        for column in inspector.get_columns("users")
    }

    # -----------------------------------------------------
    # ADD WHATSAPP NUMBER
    # -----------------------------------------------------

    if "whatsapp_number" not in columns:


        db.session.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN whatsapp_number VARCHAR(30)"
            )
        )

        db.session.commit()

    order_columns = {
        column["name"]
        for column in inspector.get_columns("orders")
    } if "orders" in tables else set()

    location_columns = {
        "delivery_latitude": "FLOAT",
        "delivery_longitude": "FLOAT",
        "delivery_location_shared": "BOOLEAN NOT NULL DEFAULT 0",
        "delivery_location_shared_at": "DATETIME",
    }

    for column_name, column_type in location_columns.items():

        if column_name not in order_columns:
            db.session.execute(text(
                f"ALTER TABLE orders ADD COLUMN "
                f"{column_name} {column_type}"
            ))
            db.session.commit()



# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def create_database():

    with app.app_context():

        db.create_all()

        migrate_database()

       
       

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

            "database": str(
                db.engine.url.database
            ),

            "categories_count":
                len(categories),

            "products_count":
                len(products_list),

            "categories": [

                {
                    "id": category.id,
                    "name": category.name
                }

                for category in categories
            ],

            "products": [

                {
                    "id": product.id,

                    "name": product.name,

                    "price": product.price,

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
        
 create_database()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
