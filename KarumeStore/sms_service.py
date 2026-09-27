import os
import requests

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

dotenv_path = os.path.join(
    os.path.dirname(__file__),
    ".env"
)

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()


# =========================================================
# SMS SERVICE CONFIGURATION
# =========================================================

SMS_SERVICE_URL = os.environ.get(
    "SMS_SERVICE_URL",
    "http://127.0.0.1:5001",
).strip().rstrip("/")

SMS_SERVICE_TOKEN = os.environ.get(
    "SMS_SERVICE_TOKEN",
    "",
).strip().strip("'\"")


# =========================================================
# OPTIONAL ENVIRONMENT FALLBACK
# =========================================================
#
# This is kept only as a fallback.
# New-order admin SMS will first try to get the
# current admin phone from the database.
#
# Therefore, changing the admin phone from
# KarumeStore Settings will work automatically.
# =========================================================

ADMIN_PHONE = os.environ.get(
    "ADMIN_PHONE",
    os.environ.get("TEST_RECIPIENT", ""),
).strip().strip("'\"")


# =========================================================
# NEW ORDER → ADMIN SMS
# =========================================================

def queue_new_order_admin_sms(
    order_id,
    order_number,
    total,
    customer_name,
    customer_phone
):

    # -----------------------------------------------------
    # IMPORT DATABASE MODELS
    # -----------------------------------------------------
    #
    # Imported inside the function to reduce the chance
    # of circular-import problems when sms_service.py
    # is imported by the orders blueprint.
    # -----------------------------------------------------

    try:

        from models import User

    except Exception:

        # If database model cannot be imported,
        # fall back to environment configuration.

        admin_phone = ADMIN_PHONE

    else:

        # -------------------------------------------------
        # FIND CURRENT ADMIN
        # -------------------------------------------------

        try:

            admin = (
                User.query
                .filter_by(role="admin")
                .first()
            )

        except Exception:

            admin = None

        # -------------------------------------------------
        # GET ADMIN PHONE FROM DATABASE
        # -------------------------------------------------

        if admin:

            admin_phone = (
                getattr(
                    admin,
                    "whatsapp_number",
                    None
                )
                or ""
            ).strip()

        else:

            admin_phone = ""

        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------
        #
        # Only use .env if there is no admin phone
        # available in the database.
        # -------------------------------------------------

        if not admin_phone:

            admin_phone = ADMIN_PHONE


    # =====================================================
    # NO ADMIN PHONE
    # =====================================================

    if not admin_phone:

        return None


    # =====================================================
    # CLEAN ADMIN PHONE
    # =====================================================

    admin_phone = (
        admin_phone
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )


    # =====================================================
    # NORMALIZE TANZANIA PHONE NUMBER
    # =====================================================

    if admin_phone.startswith("+255"):

        admin_phone = admin_phone[1:]

    elif admin_phone.startswith("0"):

        admin_phone = (
            "255" + admin_phone[1:]
        )


    # =====================================================
    # CUSTOMER INFORMATION
    # =====================================================

    name = customer_name or "Mteja"

    amount_str = (
        f"{total:,.0f}"
        if isinstance(total, (int, float))
        else str(total)
    )

    customer_phone_display = (
        customer_phone
        if customer_phone
        else "Haijawekwa"
    )


    # =====================================================
    # CREATE ADMIN MESSAGE
    # =====================================================

    message = (

        f" Kuna oda mpya #{order_number} "

        f"ya Tsh {amount_str} "

        f"kutoka kwa {name} "

        f"({customer_phone_display}). "

        f"Tafadhali ingia admin dashboard "
        f"kuichakata."
    )


    # =====================================================
    # SEND SMS TO CURRENT ADMIN PHONE
    # =====================================================

    return queue_sms(

        idempotency_key=(
            f"order-{order_id}-admin-alert"
        ),

        phone=admin_phone,

        message=message,
    )


# =========================================================
# ORDER STATUS → CUSTOMER SMS
# =========================================================

def queue_order_status_customer_sms(
    order_id,
    order_number,
    phone,
    new_status,
    customer_name=None
):

    if not phone:

        return None


    # -----------------------------------------------------
    # NORMALIZE STATUS
    # -----------------------------------------------------

    status_key = str(
        new_status or ""
    ).strip().upper()


    # -----------------------------------------------------
    # STATUS MESSAGES
    # -----------------------------------------------------

    status_texts = {

        "CONFIRMED":
            "imethibitishwa na inashughulikiwa sasa.",

        "PROCESSING":
            "inaandaliwa kikamilifu sasa.",

        "OUT_FOR_DELIVERY":
            (
                "order ipo njiani inakujia. "
                "Tafadhali kuwa karibu na simu yako."
            ),

        "DELIVERED":
            (
                "imekamilika kufikishwa. "
                "Asante kwa kununua KarumeStore!"
            ),

        "REJECTED":
            (
                "haikuweza kukamilishwa. "
                "Tafadhali wasiliana nasi "
                "kwa maelezo zaidi."
            ),

        "RECEIVED":
            (
                "tumethibitisha umepokea oda yako. "
                "Karibu tena KarumeStore!"
            ),
    }


    # -----------------------------------------------------
    # GET STATUS MESSAGE
    # -----------------------------------------------------

    status_detail = status_texts.get(

        status_key,

        f"imebadilishwa kuwa "
        f"{status_key.replace('_', ' ')}."
    )


    # -----------------------------------------------------
    # CUSTOMER GREETING
    # -----------------------------------------------------

    greeting = (

        f"Habari {customer_name}, "

        if customer_name

        else "Habari, "
    )


    # -----------------------------------------------------
    # CREATE CUSTOMER MESSAGE
    # -----------------------------------------------------

    message = (

        f"KarumeStore: "

        f"{greeting}"

        f"oda yako #{order_number} "

        f"{status_detail}"
    )


    # -----------------------------------------------------
    # SEND SMS TO CUSTOMER
    # -----------------------------------------------------

    return queue_sms(

        idempotency_key=(
            f"order-{order_id}-"
            f"status-{status_key.lower()}"
        ),

        phone=phone,

        message=message,
    )


# =========================================================
# GENERIC SMS QUEUE
# =========================================================

def queue_sms(
    idempotency_key,
    phone,
    message
):

    # -----------------------------------------------------
    # VALIDATE PHONE
    # -----------------------------------------------------

    if not phone:

        raise ValueError(
            "SMS recipient phone number is required."
        )


    # -----------------------------------------------------
    # VALIDATE MESSAGE
    # -----------------------------------------------------

    if not message:

        raise ValueError(
            "SMS message is required."
        )


    # =====================================================
    # SEND REQUEST TO KARUMESMS
    # =====================================================

    response = requests.post(

        f"{SMS_SERVICE_URL}/notifications/sms",

        json={

            "phone": phone,

            "message": message,
        },

        headers={

            "Idempotency-Key":
                idempotency_key,

            **(

                {
                    "X-Service-Token":
                        SMS_SERVICE_TOKEN
                }

                if SMS_SERVICE_TOKEN

                else {}
            ),
        },

        timeout=10,
    )


    # =====================================================
    # RAISE HTTP ERRORS
    # =====================================================

    response.raise_for_status()


    # =====================================================
    # RETURN PROVIDER RESPONSE
    # =====================================================

    return response.json()

