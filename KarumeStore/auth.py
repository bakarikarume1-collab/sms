from functools import wraps
import re
from flask import redirect, url_for

from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Cart,PasswordReset
import secrets

from datetime import datetime, timedelta
from utils.email_service import send_otp_email

 

# =========================================================
# AUTH BLUEPRINT
# =========================================================

auth = Blueprint("auth", __name__)


def password_policy_error(password):

    if len(password) < 8:
        return "Password must be at least 8 characters."

    if not re.search(r"[A-Z]", password):
        return "Password must contain an uppercase letter."

    if not re.search(r"[a-z]", password):
        return "Password must contain a lowercase letter."

    if not re.search(r"\d", password):
        return "Password must contain a number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain a special character."

    return None


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    user = db.session.get(User, user_id)

    if not user or not user.is_active:
        session.clear()
        return None

    return user


# =========================================================
# USER TO DICTIONARY
# =========================================================

def user_to_dict(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "whatsapp_number": user.whatsapp_number,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        )
    }


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        user = get_current_user()

        if not user:
            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        return fn(*args, **kwargs)

    return wrapper


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        user = get_current_user()

        if not user:
            return jsonify({
                "success": False,
                "message": "Login required."
            }), 401

        if user.role != "admin":
            return jsonify({
                "success": False,
                "message": "Admin access required."
            }), 403

        return fn(*args, **kwargs)

    return wrapper


# =========================================================
# REGISTER
# =========================================================

@auth.post("/api/auth/register")
def register():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    whatsapp_number = str(
        data.get("whatsapp_number", "")
    ).strip()


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not name:
        return jsonify({
            "success": False,
            "message": "Name is required."
        }), 400

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    if not password:
        return jsonify({
            "success": False,
            "message": "Password is required."
        }), 400

    if not whatsapp_number:
        return jsonify({
            "success": False,
            "message": "phone number is required."
        }), 400

    password_error = password_policy_error(password)

    if password_error:
        return jsonify({
            "success": False,
            "message": password_error
        }), 400


    # -----------------------------------------------------
    # CHECK EMAIL
    # -----------------------------------------------------

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return jsonify({
            "success": False,
            "message": "Email is already registered."
        }), 409


    # -----------------------------------------------------
    # CREATE USER
    # -----------------------------------------------------

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        whatsapp_number=whatsapp_number,
        role="customer"
    )

    db.session.add(user)

    
    db.session.flush()



    # -----------------------------------------------------
    # CREATE CART
    # -----------------------------------------------------

    cart = Cart(
        user_id=user.id
    )

    db.session.add(cart)


    # -----------------------------------------------------
    # SAVE DATABASE
    # -----------------------------------------------------

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Registration failed. Please try again."
        }), 500


    # -----------------------------------------------------
    # LOGIN USER AUTOMATICALLY
    # -----------------------------------------------------

    session.permanent = True

    session["user_id"] = user.id

    sms_notification = {
        "queued": False,
        "status": "UNAVAILABLE",
    }

    try:

        result = queue_welcome_sms(
            user_id=user.id,
            name=user.name,
            phone=user.whatsapp_number,
        )

        sms_notification = {
            "queued": True,
            "status": result.get("status", "PENDING"),
            "sms_id": result.get("sms_id"),
        }

    except Exception as exc:

        print(
            f"[AUTH] Welcome SMS was not queued: {exc}"
        )


    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": user_to_dict(user),
        "sms_notification": sms_notification,
    }), 201

@auth.put("/api/auth/account")
@login_required
def update_account():

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Not authenticated.",
            "redirect":"/login"
        }), 401
        
        

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    whatsapp_number = str(
        data.get("whatsapp_number", "")
    ).strip()


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not name:
        return jsonify({
            "success": False,
            "message": "Name is required."
        }), 400

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    if not whatsapp_number:
        return jsonify({
            "success": False,
            "message": "Phone number is required."
        }), 400


    # -----------------------------------------------------
    # CHECK EMAIL
    # -----------------------------------------------------

    existing_user = User.query.filter(
        User.email == email,
        User.id != user.id
    ).first()

    if existing_user:
        return jsonify({
            "success": False,
            "message": "Email is already registered by another account."
        }), 409


    # -----------------------------------------------------
    # UPDATE USER
    # -----------------------------------------------------

    user.name = name
    user.email = email
    user.whatsapp_number = whatsapp_number


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        print(
            f"[AUTH] Account update failed: {exc}"
        )

        return jsonify({
            "success": False,
            "message": "Failed to update account. Please try again."
        }), 500


    return jsonify({
        "success": True,
        "message": "Account updated successfully.",
        "user": user_to_dict(user)
    }), 200



@auth.put("/api/auth/password")
def update_password():

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Not authenticated."
        }), 401


    data = request.get_json(silent=True) or {}

    current_password = str(
        data.get("current_password", "")
    )

    new_password = str(
        data.get("new_password", "")
    )

    confirm_password = str(
        data.get("confirm_password", "")
    )


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not current_password:
        return jsonify({
            "success": False,
            "message": "Current password is required."
        }), 400

    if not new_password:
        return jsonify({
            "success": False,
            "message": "New password is required."
        }), 400

    if not confirm_password:
        return jsonify({
            "success": False,
            "message": "Please confirm your new password."
        }), 400


    # -----------------------------------------------------
    # CHECK CURRENT PASSWORD
    # -----------------------------------------------------

    if not check_password_hash(
        user.password_hash,
        current_password
    ):
        return jsonify({
            "success": False,
            "message": "Current password is incorrect."
        }), 401


    # -----------------------------------------------------
    # CHECK NEW PASSWORD
    # -----------------------------------------------------

    password_error = password_policy_error(
        new_password
    )

    if password_error:
        return jsonify({
            "success": False,
            "message": password_error
        }), 400


    # -----------------------------------------------------
    # CONFIRM PASSWORD
    # -----------------------------------------------------

    if new_password != confirm_password:
        return jsonify({
            "success": False,
            "message": "New passwords do not match."
        }), 400


    # -----------------------------------------------------
    # PREVENT SAME PASSWORD
    # -----------------------------------------------------

    if check_password_hash(
        user.password_hash,
        new_password
    ):
        return jsonify({
            "success": False,
            "message": "New password must be different from your current password."
        }), 400


    # -----------------------------------------------------
    # UPDATE PASSWORD
    # -----------------------------------------------------

    user.password_hash = generate_password_hash(
        new_password
    )


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        print(
            f"[AUTH] Password update failed: {exc}"
        )

        return jsonify({
            "success": False,
            "message": "Failed to update password. Please try again."
        }), 500


    return jsonify({
        "success": True,
        "message": "Password changed successfully."
    }), 200

    #==================================
    # RESERT PASSWORD PATH
    #==================================



@auth.post("/api/auth/forgot-password")
def forgot_password():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()


    # ==========================================
    # CHECK EMAIL
    # ==========================================

    if not email:

        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400


    # ==========================================
    # FIND USER
    # ==========================================

    user = User.query.filter_by(
        email=email
    ).first()


    # ==========================================
    # USER NOT FOUND
    # ==========================================

    if not user:

        return jsonify({
            "success": False,
            "message": "No account found with that email."
        }), 404


    # ==========================================
# INVALIDATE OLD OTPs
# ==========================================

    PasswordReset.query.filter_by(
        user_id=user.id,
        used=False
    ).update({
        "used": True
    })


    # ==========================================
    # GENERATE 6-DIGIT OTP
    # ==========================================

    otp = f"{secrets.randbelow(1000000):06d}"


    # ==========================================
    # HASH OTP
    # ==========================================

    otp_hash = generate_password_hash(otp)


    # ==========================================
    # EXPIRATION TIME
    # ==========================================

    expires_at = datetime.utcnow() + timedelta(
        minutes=10
    )


    # ==========================================
    # CREATE PASSWORD RESET RECORD
    # ==========================================

    reset = PasswordReset(
        user_id=user.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        used=False
    )


    db.session.add(reset)

    db.session.commit()


    # ==========================================
# SEND OTP EMAIL
# ==========================================

    try:

        send_otp_email(
            email,
            otp
        )

    except Exception as e:

        print(
            "Email sending error:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Unable to send OTP email."
        }), 500


    # ==========================================
    # SUCCESS
    # ==========================================

    return jsonify({
            "success": True,
            "message": "OTP has been sent to your email."
        })

#=====================================
###### END OF RESET PASSWORD==================
#======================================

#========================================
#   verify otp

#=======================================

@auth.post("/api/auth/verify-otp")
def verify_otp():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    otp = str(
        data.get("otp", "")
    ).strip()


    # ==========================================
    # CHECK INPUT
    # ==========================================

    if not email or not otp:

        return jsonify({
            "success": False,
            "message": "Email and OTP are required."
        }), 400


    # ==========================================
    # FIND USER
    # ==========================================

    user = User.query.filter_by(
        email=email
    ).first()

    if not user:

        return jsonify({
            "success": False,
            "message": "Invalid OTP."
        }), 400


    # ==========================================
    # FIND ACTIVE RESET
    # ==========================================

    reset = (
        PasswordReset.query
        .filter_by(
            user_id=user.id,
            used=False
        )
        .order_by(
            PasswordReset.created_at.desc()
        )
        .first()
    )


    if not reset:

        return jsonify({
            "success": False,
            "message": "OTP is invalid or expired."
        }), 400


    # ==========================================
    # CHECK EXPIRATION
    # ==========================================

    if datetime.utcnow() > reset.expires_at:

        reset.used = True

        db.session.commit()

        return jsonify({
            "success": False,
            "message": "OTP has expired."
        }), 400


    # ==========================================
    # CHECK ATTEMPTS
    # ==========================================

    if reset.attempts >= 3:

        reset.used = True

        db.session.commit()

        return jsonify({
            "success": False,
            "message": "Too many incorrect attempts."
        }), 429



    # ==========================================
    # VERIFY OTP
    # ==========================================

    if not check_password_hash(
        reset.otp_hash,
        otp
    ):

        reset.attempts += 1

        db.session.commit()

        return jsonify({
            "success": False,
            "message": "Invalid OTP."
        }), 400


    # ==========================================
    # OTP VERIFIED
    # ==========================================

    session["password_reset_user_id"] = user.id
    session["password_reset_verified"] = True

    return jsonify({
        "success": True,
        "message": "OTP verified successfully."
    })



@auth.post("/api/auth/reset-password")
def reset_password():

    data = request.get_json(silent=True) or {}

    password = str(
        data.get("password", "")
    )

    confirm_password = str(
        data.get("confirm_password", "")
    )


    # ==========================================
    # CHECK RESET AUTHORIZATION
    # ==========================================

    if not session.get("password_reset_verified"):

        return jsonify({
            "success": False,
            "message": "OTP verification is required."
        }), 403


    user_id = session.get(
        "password_reset_user_id"
    )


    # ==========================================
    # CHECK PASSWORD
    # ==========================================

    if not password or not confirm_password:

        return jsonify({
            "success": False,
            "message": "Password and confirmation are required."
        }), 400


    # ==========================================
    # CHECK PASSWORD MATCH
    # ==========================================

    if password != confirm_password:

        return jsonify({
            "success": False,
            "message": "Passwords do not match."
        }), 400


    # ==========================================
    # PASSWORD LENGTH
    # ==========================================

    password_error = password_policy_error(password)

    if password_error:

        return jsonify({
            "success": False,
            "message": password_error
        }), 400


    # ==========================================
    # FIND USER
    # ==========================================

    user = User.query.get(user_id)

    if not user:

        return jsonify({
            "success": False,
            "message": "User account not found."
        }), 404


    # ==========================================
    # HASH NEW PASSWORD
    # ==========================================

    user.password_hash = generate_password_hash(
        password
    )


    # ==========================================
    # MARK OTP AS USED
    # ==========================================

    reset = (
        PasswordReset.query
        .filter_by(
            user_id=user.id,
            used=False
        )
        .order_by(
            PasswordReset.created_at.desc()
        )
        .first()
    )

    if reset:
        reset.used = True


    # ==========================================
    # SAVE
    # ==========================================

    db.session.commit()


    # ==========================================
    # CLEAR RESET SESSION
    # ==========================================

    session.pop(
        "password_reset_user_id",
        None
    )

    session.pop(
        "password_reset_verified",
        None
    )


    return jsonify({
        "success": True,
        "message": "Password reset successfully."
    })



# =========================================================
# LOGIN
# =========================================================

@auth.post("/api/auth/login")
def login():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )


    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400


    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = User.query.filter_by(
        email=email
    ).first()


    if not user:

        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401



    # -----------------------------------------------------
    # CHECK ACCOUNT
    # -----------------------------------------------------

    if not user.is_active:

        return jsonify({
            "success": False,
            "message": "Your account is inactive."
        }), 403


    # -----------------------------------------------------
    # CHECK PASSWORD
    # -----------------------------------------------------

    if not check_password_hash(
        user.password_hash,
        password
    ):

        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401


    # -----------------------------------------------------
    # CREATE SESSION
    # -----------------------------------------------------

    session.permanent = True

    session["user_id"] = user.id


    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user_to_dict(user)
    })


# =========================================================
# LOGOUT
# =========================================================

# =========================================================
# LOGOUT
# =========================================================

@auth.post("/api/auth/logout")
def logout():

    # -----------------------------------------------------
    # CHECK IF USER IS LOGGED IN
    # -----------------------------------------------------

    user = get_current_user()

    if not user:

        return jsonify({
            "success": False,
            "message": "Not authenticated."
        }), 401

    # -----------------------------------------------------
    # CLEAR AUTHENTICATION SESSION
    # -----------------------------------------------------

    session.clear()

    # -----------------------------------------------------
    # SUCCESS RESPONSE
    # -----------------------------------------------------

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200

# =========================================================
# CURRENT USER
# =========================================================

@auth.get("/api/auth/me")
def me():

    user = get_current_user()

    if not user:

        return jsonify({
            "success": False,
            "message": "Not authenticated."
        }), 401


    return jsonify({
        "success": True,
        "user": user_to_dict(user)
    })