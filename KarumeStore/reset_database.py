from app import app
from models import db, Category, Product, ProductImage


# =========================================================
# CATEGORIES
# =========================================================

CATEGORIES = [
    "Clothes",
    "Shoes",
    "Fridges",
    "Electronics",
    "Bags",
    "phones",
    "Accessories",
    "Home Appliances"
]


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = [

    (
        "Premium Black T-Shirt",
        "High quality cotton black T-shirt.",
        25000,
        20000,
        50,
        "Clothes",
        True,
        "/static/images/clothes.jpg"
    ),

    (
        "Classic Blue Jeans",
        "Comfortable modern blue jeans.",
        65000,
        55000,
        30,
        "Clothes",
        True,
        "/static/images/men dresing.jpg"
    ),

    (
        "Men's Casual Sneakers",
        "Stylish sneakers for everyday use.",
        85000,
        75000,
        25,
        "Shoes",
        True,
        "/static/images/shoose.jpg"
    ),

    (
        "Smart Digital phones",
        "Modern digital phones.",
        120000,
        99000,
        15,
        "phones",
        True,
        "/static/images/phones11.jpg"
    ),

    (
        "Premium Travel Backpack",
        "Strong and spacious backpack.",
        70000,
        60000,
        20,
        "Bags",
        False,
        "/static/images/15.jpg"
    ),

    (
        "Double Door Refrigerator",
        "Large capacity double door refrigerator.",
        1250000,
        1150000,
        8,
        "Fridges",
        True,
        "/static/images/two door.jpg"
    ),

    (
        "Bluetooth Speaker",
        "Portable wireless Bluetooth speaker.",
        95000,
        80000,
        35,
        "Electronics",
        False,
        "/static/images/hearphone.jpg"
    ),

    (
        "Electric Blender",
        "Powerful kitchen blender.",
        110000,
        95000,
        18,
        "Home Appliances",
        False,
        "/static/images/brender.jpg"
    ),

    (
        "Leather fashion",
        "Premium leather fashion.",
        35000,
        30000,
        40,
        "Clothes",
        False,
        "/static/images/harusi.jpg"
    ),

    (
        "washing machine for more shinnig",
        "Comfortable shinning.",
        1300000,
        1200000,
        30,
        "Home Appliances",
        True,
        "/static/images/wahing.jpg"
    ),

    (
        "Smart Tv",
        "Smart Tv for more vision and quality.",
        200000,
        180000,
        35,
        "Electronics",
        False,
        "/static/images/Tv.jpg"
    )

]


# =========================================================
# RESET DATABASE
# =========================================================

with app.app_context():


    db.drop_all()

    # -----------------------------------------------------
    # CREATE TABLES
    # -----------------------------------------------------

    print("Creating tables...")

    db.create_all()

    # -----------------------------------------------------
    # CREATE CATEGORIES
    # -----------------------------------------------------

    print("\nCreating categories...")

    category_objects = {}

    for category_name in CATEGORIES:

        category = Category(
            name=category_name
        )

        db.session.add(category)

        category_objects[category_name] = category

    db.session.commit()

    print(
        f"Created {len(CATEGORIES)} categories."
    )

    # -----------------------------------------------------
    # CREATE PRODUCTS
    # -----------------------------------------------------

    print("\nCreating products...")

    for item in PRODUCTS:

        (
            name,
            description,
            price,
            discount_price,
            stock,
            category_name,
            is_featured,
            image_url
        ) = item

        # Get category
        category = category_objects.get(
            category_name
        )

        if not category:

            print(
                f"WARNING: Category not found: "
                f"{category_name}"
            )

            continue

        # -----------------------------------------------
        # CREATE PRODUCT
        # -----------------------------------------------

        product = Product(

            name=name,

            description=description,

            price=price,

            discount_price=discount_price,

            stock=stock,

            is_featured=is_featured,

            category_id=category.id
        )

        db.session.add(product)

        # We need the product ID before creating

        db.session.flush()

        # -----------------------------------------------
        # CREATE PRODUCT IMAGE
        # -----------------------------------------------

        image = ProductImage(

            product_id=product.id,

            image_url=image_url,

            is_primary=True
        )

        db.session.add(image)

    # -----------------------------------------------------
    # SAVE EVERYTHING
    # -----------------------------------------------------

    db.session.commit()

    # =====================================================
    # VERIFY
    # =====================================================

    print("\n===================================")
    print("DATABASE VERIFICATION")
    print("===================================")

    category_count = Category.query.count()

    product_count = Product.query.count()

    image_count = ProductImage.query.count()


    # -----------------------------------------------------
    # SHOW PRODUCTS + IMAGES
    # -----------------------------------------------------

    print("\n===================================")
    print("PRODUCTS")
    print("===================================")

    products = Product.query.order_by(
        Product.id.asc()
    ).all()

    for product in products:

        category_name = (
            product.category.name
            if product.category
            else "NO CATEGORY"
        )

        print(
            f"\n{product.id}. {product.name}"
        )

        print(
            f"   Price: {product.price}"
        )

        print(
            f"   Category: {category_name}"
        )

        for image in product.images:

            print(
                f"   Image: {image.image_url}"
            )
