from flask import Blueprint, render_template, redirect, url_for
from admin import admin_required
from auth import get_current_user, login_required

pages = Blueprint("pages", __name__)


# ============================================================
# PUBLIC PAGES
# ============================================================

@pages.get("/")
def home():
    return render_template("index.html")


@pages.get("/products")
def products_page():
    return render_template("products.html")


@pages.get("/product/<int:product_id>")
def product_page(product_id):
    return render_template(
        "product.html",
        product_id=product_id
    )


@pages.get("/cart")
def cart_page():

    user = get_current_user()

    if not user:
        return redirect(url_for("pages.login_page"))

    return render_template("cart.html")


   

@pages.get("/checkout")
def checkout_page():
    return render_template("checkout.html")



@pages.get("/login")
def login_page():
    return render_template("login.html")


@pages.get("/register")
def register_page():
    return render_template("register.html")


@pages.get("/orders")
def orders_page():
    return render_template("orders.html")


@pages.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot-password.html")


@pages.get("/reset-password")
def reset_password_page():
    return render_template("reset-password.html")


@pages.get("/verify-otp")
def verify_otp_page():
    return render_template("verify-otp.html")


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@pages.get("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")


# ============================================================
# ADMIN SALES
# ============================================================

@pages.get("/admin/sales")
@admin_required
def admin_sales_page():
    return render_template("admin_sales.html")


# ============================================================
# ADMIN ORDERS
# ============================================================

@pages.get("/admin/orders")
@admin_required
def admin_orders_page():
    return render_template("admin_orders.html")


# ============================================================
# ADMIN PRODUCTS
# ============================================================

@pages.get("/admin/products")
@admin_required
def admin_products_page():
    return render_template("admin_products.html")


@pages.get("/admin/products/new")
@admin_required
def admin_product_new_page():
    return render_template("admin_product_new.html")


@pages.get("/admin/products/<int:product_id>/edit")
@admin_required
def admin_product_edit_page(product_id):
    return render_template(
        "admin_product_edit.html",
        product_id=product_id
    )


# ============================================================
# ADMIN CUSTOMERS
# ============================================================

@pages.get("/admin/customers")
@admin_required
def admin_customers_page():
    return render_template("admin_customers.html")


# ============================================================
# ADMIN SMS
# ============================================================

@pages.get("/admin/sms")
@admin_required
def admin_sms_page():
    return render_template("admin_sms.html")


# ============================================================
# ADMIN SETTINGS
# ============================================================

@pages.get("/admin/settings")
@admin_required
def admin_settings_page():
    return render_template("admin_settings.html")

@pages.get("/account")
def account():

    user = get_current_user()

    if not user:
        return redirect(url_for("pages.login_page"))

    # Admin hatakiwi kutumia customer account page
    if user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "account.html",
        user=user
    )


@pages.route("/logout")
def logout():
    return render_template ("login.html")

