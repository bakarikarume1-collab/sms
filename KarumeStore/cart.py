
from flask import Blueprint, current_app, jsonify, request

from auth import login_required, get_current_user
from models import db, Cart, CartItem, Product


cart = Blueprint("cart", __name__)


# =========================================================
# CART ITEM SERIALIZER
# =========================================================

def item_to_dict(item):

    price = (
        item.product.discount_price
        if item.product.discount_price is not None
        else item.product.price
    )

    return {
        "id": item.id,

        "product_id": item.product_id,

        "quantity": item.quantity,

        "unit_price": price,

        "total": price * item.quantity,

        "product": {
            "id": item.product.id,

            "name": item.product.name,

            "stock": item.product.stock,

            "is_active": bool(
                item.product.is_active
            ),

            "image": (
                next(
                    (
                        x.image_url
                        for x in item.product.images
                        if x.is_primary
                    ),
                    None
                )
                or (
                    item.product.images[0].image_url
                    if item.product.images
                    else None
                )
            )
        }
    }


# =========================================================
# GET CART
# =========================================================

@cart.get("/api/cart")
@login_required
def get_cart():

    user = get_current_user()

    # -----------------------------------------------------
    # CREATE CART IF USER DOES NOT HAVE ONE
    # -----------------------------------------------------

    if not user.cart:

        user.cart = Cart(
            user_id=user.id
        )

        db.session.commit()

    # -----------------------------------------------------
    # GET ALL CART ITEMS
    #
    # IMPORTANT:
    # We DO NOT remove inactive products here.
    # If admin deactivates a product that was already
    # inside a customer's cart, the item remains visible.
    # -----------------------------------------------------

    items = [
        item_to_dict(item)
        for item in user.cart.items
    ]

    # -----------------------------------------------------
    # CALCULATE SUBTOTAL
    # -----------------------------------------------------

    subtotal = sum(
        item["total"]
        for item in items
    )

    # -----------------------------------------------------
    # CART RESPONSE
    # -----------------------------------------------------

    return jsonify({

        "success": True,

        "cart": {

            "id": user.cart.id,

            "items": items,

            "subtotal": subtotal,

            "item_count": sum(
                item["quantity"]
                for item in items
            )
        }
    })


# =========================================================
# ADD ITEM TO CART
# =========================================================

@cart.post("/api/cart/items")
@login_required
def add_item():

    user = get_current_user()

    data = request.get_json(
        silent=True
    ) or {}

    # =====================================================
    # GET PRODUCT ID AND QUANTITY
    # =====================================================

    product_id = data.get(
        "product_id"
    )

    quantity = data.get(
        "quantity",
        1
    )

    # =====================================================
    # VALIDATE PRODUCT ID AND QUANTITY
    # =====================================================

    try:

        product_id = int(
            product_id
        )

        quantity = int(
            quantity
        )

    except (TypeError, ValueError):

        return jsonify({

            "success": False,

            "message":
                "Invalid product or quantity."

        }), 400

    # =====================================================
    # QUANTITY MUST BE AT LEAST 1
    # =====================================================

    if quantity < 1:

        return jsonify({

            "success": False,

            "message":
                "Quantity must be at least 1."

        }), 400

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

            "message":
                "Product not found."

        }), 404

    # =====================================================
    # CHECK PRODUCT ACTIVE STATUS
    #
    # An inactive product cannot be newly added
    # to a customer's cart.
    # =====================================================

    if not product.is_active:

        return jsonify({

            "success": False,

            "message":
                f"{product.name} is currently unavailable."

        }), 400

    # =====================================================
    # CHECK IF PRODUCT IS OUT OF STOCK
    # =====================================================

    if product.stock <= 0:

        return jsonify({

            "success": False,

            "message":
                f"{product.name} is currently "
                "out of stock."

        }), 400

    # =====================================================
    # CHECK REQUESTED QUANTITY
    # =====================================================

    if quantity > product.stock:

        return jsonify({

            "success": False,

            "message":
                f"Only {product.stock} unit(s) "
                f"of {product.name} are available."

        }), 400

    # =====================================================
    # CREATE CART IF CUSTOMER DOES NOT HAVE ONE
    # =====================================================

    if not user.cart:

        user.cart = Cart(
            user_id=user.id
        )

        db.session.flush()

    # =====================================================
    # CHECK IF PRODUCT ALREADY EXISTS IN CART
    # =====================================================

    item = CartItem.query.filter_by(

        cart_id=user.cart.id,

        product_id=product.id

    ).first()

    # =====================================================
    # PRODUCT ALREADY EXISTS IN CART
    # =====================================================

    if item:

        new_quantity = (
            item.quantity + quantity
        )

        # -------------------------------------------------
        # CHECK TOTAL CART QUANTITY AGAINST STOCK
        # -------------------------------------------------

        if new_quantity > product.stock:

            return jsonify({

                "success": False,

                "message":
                    f"You can only have "
                    f"{product.stock} unit(s) of "
                    f"{product.name} in your cart."

            }), 400

        item.quantity = new_quantity

    # =====================================================
    # NEW CART ITEM
    # =====================================================

    else:

        item = CartItem(

            cart_id=user.cart.id,

            product_id=product.id,

            quantity=quantity
        )

        db.session.add(item)

    # =====================================================
    # SAVE CART
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to add product to cart"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to add product to cart."

        }), 500

    # =====================================================
    # CALCULATE CART COUNT
    # =====================================================

    cart_count = sum(

        cart_item.quantity

        for cart_item in user.cart.items
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            f"{product.name} added to cart.",

        "cart_count":
            cart_count,

        "item_quantity":
            item.quantity,

        "product_stock":
            product.stock

    }), 200


# =========================================================
# UPDATE CART ITEM
# =========================================================

@cart.put("/api/cart/items/<int:item_id>")
@login_required
def update_item(item_id):

    user = get_current_user()

    item = db.session.get(
        CartItem,
        item_id
    )

    # -----------------------------------------------------
    # VERIFY CART ITEM BELONGS TO CURRENT USER
    # -----------------------------------------------------

    if (
        not item
        or not user.cart
        or item.cart_id != user.cart.id
    ):

        return jsonify({

            "success": False,

            "message":
                "Cart item not found."

        }), 404

    # =====================================================
    # GET QUANTITY
    # =====================================================

    data = request.get_json(
        silent=True
    ) or {}

    try:

        quantity = int(
            data.get("quantity")
        )

    except (TypeError, ValueError):

        return jsonify({

            "success": False,

            "message":
                "Invalid quantity."

        }), 400

    # =====================================================
    # CHECK PRODUCT ACTIVE STATUS
    #
    # IMPORTANT:
    # The item remains in the cart even if inactive.
    # But customer cannot modify its quantity.
    # =====================================================

    if not item.product.is_active:

        return jsonify({

            "success": False,

            "message":
                f"{item.product.name} is currently "
                "unavailable."

        }), 400

    # =====================================================
    # CHECK QUANTITY AGAINST STOCK
    # =====================================================

    if (
        quantity < 1
        or quantity > item.product.stock
    ):

        return jsonify({

            "success": False,

            "message":
                "Invalid quantity or insufficient stock."

        }), 400

    # =====================================================
    # UPDATE QUANTITY
    # =====================================================

    item.quantity = quantity

    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to update cart item"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to update cart."

        }), 500

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            "Cart updated."

    }), 200


# =========================================================
# DELETE SINGLE CART ITEM
# =========================================================

@cart.delete("/api/cart/items/<int:item_id>")
@login_required
def delete_item(item_id):

    user = get_current_user()

    item = db.session.get(
        CartItem,
        item_id
    )

    # -----------------------------------------------------
    # VERIFY CART ITEM BELONGS TO CURRENT USER
    # -----------------------------------------------------

    if (
        not item
        or not user.cart
        or item.cart_id != user.cart.id
    ):

        return jsonify({

            "success": False,

            "message":
                "Cart item not found."

        }), 404

    # =====================================================
    # DELETE ITEM
    # =====================================================

    db.session.delete(item)

    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to remove cart item"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to remove item."

        }), 500

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            "Item removed."

    }), 200


# =========================================================
# CLEAR CART
# =========================================================

@cart.delete("/api/cart")
@login_required
def clear_cart():

    user = get_current_user()

    # -----------------------------------------------------
    # IF USER HAS NO CART
    # -----------------------------------------------------

    if not user.cart:

        return jsonify({

            "success": True,

            "message":
                "Cart cleared."

        }), 200

    # =====================================================
    # DELETE ALL CART ITEMS
    # =====================================================

    CartItem.query.filter_by(

        cart_id=user.cart.id

    ).delete()

    # =====================================================
    # SAVE
    # =====================================================

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to clear cart"
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to clear cart."

        }), 500

    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "message":
            "Cart cleared."

    }), 200

