import os

from werkzeug.security import generate_password_hash

from app import app
from models import (
    db,
    User,
    Cart,
    Category,
    Product,
    ProductImage
)


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
#
# IMPORTANT:
# Change the image filenames below to match your
# actual files inside:
#
# static/images/
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
            "Comfortable shinning  .",
            1300000,
            1200000,
            30,
            "Home Appliances",
            True,
            "/static/images/wahing.jpg"
        ),
        (
                "Smart Tv",
                "Smart Tv for more vission and quallity.",
                200000,
                180000,
                35,
                "Electronics",
                False,
                "/static/images/Tv.jpg"
            )

]


# =========================================================
# SEED DATABASE
# =========================================================

with app.app_context():

    print("========================================")
    print("   KARUMESTORE DATABASE SEED")
    print("========================================")


    # -----------------------------------------------------
    # CREATE TABLES
    # -----------------------------------------------------

    db.create_all()

    print("Database tables checked.")


    # -----------------------------------------------------
    # CREATE / GET CATEGORIES
    # -----------------------------------------------------

    category_map = {}

    for category_name in CATEGORIES:

        category = Category.query.filter_by(
            name=category_name
        ).first()


        if not category:

            category = Category(
                name=category_name
            )

            db.session.add(category)

            db.session.flush()

            print(
                f"Created category: {category_name}"
            )

        else:

            print(
                f"Category exists: {category_name}"
            )


        category_map[category_name] = category


    # -----------------------------------------------------
    # CREATE / UPDATE PRODUCTS
    # -----------------------------------------------------

    for (
        name,
        description,
        price,
        discount,
        stock,
        category_name,
        featured,
        image_url
    ) in PRODUCTS:


        product = Product.query.filter_by(
            name=name
        ).first()


        # =================================================
        # CREATE PRODUCT
        # =================================================

        if not product:

            product = Product(

                name=name,

                description=description,

                price=price,

                discount_price=discount,

                stock=stock,

                is_featured=featured,

                category_id=category_map[
                    category_name
                ].id

            )

            db.session.add(product)

            db.session.flush()

            print(
                f"Created product: {name}"
            )


        # =================================================
        # UPDATE EXISTING PRODUCT
        # =================================================

        else:

            product.description = description

            product.price = price

            product.discount_price = discount

            product.stock = stock

            product.is_featured = featured

            product.category_id = (
                category_map[
                    category_name
                ].id
            )



        # =================================================
        # PRODUCT IMAGE
        # =================================================

        primary_image = (
            ProductImage.query
            .filter_by(
                product_id=product.id,
                is_primary=True
            )
            .first()
        )


        # -------------------------------------------------
        # If primary image exists -> UPDATE it
        # -------------------------------------------------

        if primary_image:

            primary_image.image_url = image_url

            print(
                f"Updated image: {image_url}"
            )


        # -------------------------------------------------
        # If no primary image -> CREATE it
        # -------------------------------------------------

        else:

            old_images = ProductImage.query.filter_by(
                product_id=product.id
            ).all()


            for old_image in old_images:

                db.session.delete(
                    old_image
                )


            db.session.flush()


            new_image = ProductImage(

                product_id=product.id,

                image_url=image_url,

                is_primary=True

            )

            db.session.add(
                new_image
            )

           


    # =====================================================
    # ADMIN ACCOUNT
    # =====================================================

    admin_email = os.environ.get("ADMIN_EMAIL")

    admin_password = os.environ.get("ADMIN_PASSWORD")


    admin_user = User.query.filter_by(
        email=admin_email
    ).first()


    if not admin_user:

        admin_user = User(

            name="Store Admin",

            email=admin_email,

            password_hash=generate_password_hash(
                admin_password
            ),

            role="admin"

        )

        db.session.add(
            admin_user
        )

        print(
            "Created admin account."
        )


    else:

        print(
            "Admin account already exists."
        )



    db.session.commit()
