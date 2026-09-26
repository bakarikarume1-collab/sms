from flask import Blueprint, jsonify, request
from models import db, Product, Category

products = Blueprint("products", __name__)


# =========================================================
# PRODUCT SERIALIZER
# =========================================================

def product_to_dict(product):
    """
    Convert Product object into JSON-friendly dictionary.
    Includes category + all images + primary image.
    """

    images = []

    for img in product.images:

        if img.image_url:

            images.append({
                "id": img.id,
                "image_url": img.image_url,
                "is_primary": bool(img.is_primary)
            })


    # Find primary image
    primary_image = None

    for image in images:

        if image["is_primary"]:

            primary_image = image["image_url"]

            break


    # If no primary image, use first image
    if not primary_image and images:

        primary_image = images[0]["image_url"]


    return {
        "id": product.id,

        "name": product.name,

        "description": product.description or "",

        "price": product.price,

        "discount_price": product.discount_price,

        "stock": product.stock,

        "is_featured": bool(product.is_featured),

        "category": (
            {
                "id": product.category.id,
                "name": product.category.name
            }
            if product.category
            else None
        ),

        "images": images,

        "primary_image": primary_image
    }


# =========================================================
# GET ALL CATEGORIES
# =========================================================

@products.get("/api/categories")
def get_categories():

    categories = (
        Category.query
        .order_by(Category.name.asc())
        .all()
    )

    return jsonify([

        {
            "id": category.id,
            "name": category.name
        }

        for category in categories

    ])


# =========================================================
# GET SINGLE CATEGORY
# =========================================================

@products.get("/api/categories/<int:category_id>")
def get_category(category_id):

    category = db.session.get(
        Category,
        category_id
    )


    if not category:

        return jsonify({
            "success": False,
            "message": "Category not found."
        }), 404


    return jsonify({

        "id": category.id,

        "name": category.name,

        "products": [

            product_to_dict(product)

            for product in category.products

            # ONLY ACTIVE PRODUCTS
            if product.is_active

        ]

    })


# =========================================================
# GET ALL PRODUCTS
# =========================================================

@products.get("/api/products")
def get_products():

    search = request.args.get(
        "search",
        ""
    ).strip()


    # IMPORTANT:
    # Frontend may send either:
    #
    # ?category=5
    #
    # OR
    #
    # ?category_id=5
    #
    category_id = request.args.get(
        "category_id",
        type=int
    )


    if category_id is None:

        category_id = request.args.get(
            "category",
            type=int
        )


    # =====================================================
    # ONLY ACTIVE PRODUCTS
    # =====================================================

    query = Product.query.filter(
        Product.is_active.is_(True)
    )


    # =====================================================
    # SEARCH
    # =====================================================

    if search:

        query = query.filter(

            db.or_(

                Product.name.ilike(
                    f"%{search}%"
                ),

                Product.description.ilike(
                    f"%{search}%"
                )

            )

        )


    # =====================================================
    # CATEGORY FILTER
    # =====================================================

    if category_id is not None:

        query = query.filter(
            Product.category_id == category_id
        )


    # =====================================================
    # GET PRODUCTS
    # =====================================================

    products_list = (
        query
        .order_by(Product.id.desc())
        .all()
    )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify([

        product_to_dict(product)

        for product in products_list

    ])


# =========================================================
# FEATURED PRODUCTS
# =========================================================

@products.get("/api/products/featured")
def get_featured_products():

    featured_products = (

        Product.query

        .filter(
            Product.is_featured.is_(True),
            Product.is_active.is_(True)
        )

        .order_by(
            Product.id.desc()
        )

        .all()

    )


    return jsonify([

        product_to_dict(product)

        for product in featured_products

    ])


# =========================================================
# GET SINGLE PRODUCT
# =========================================================

@products.get("/api/products/<int:product_id>")
def get_product(product_id):

    product = (

        Product.query

        .filter(
            Product.id == product_id,
            Product.is_active.is_(True)
        )

        .first()

    )


    # Product does not exist
    # OR product has been deactivated
    if not product:

        return jsonify({

            "success": False,

            "message": "Product not found."

        }), 404


    return jsonify(
        product_to_dict(product)
    )