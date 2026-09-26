
import secrets
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request

from config import (
    FRONTEND_ORIGINS,
    SMS_SERVICE_TOKEN,
    SMS_API_KEY,
    SMS_API_URL,
    SMS_SENDER_ID,
    SMS_RATE_LIMIT_PER_MINUTE,
    TEST_RECIPIENT,
)

from sms.client import SMSClient
from database.models import create_tables
from bulk_api import bulk


app = Flask(__name__)
create_tables()
app.register_blueprint(bulk)

queue_requests = defaultdict(deque)


def service_token_error():

    if not SMS_SERVICE_TOKEN:
        return None

    provided = request.headers.get("X-Service-Token", "")

    if not secrets.compare_digest(provided, SMS_SERVICE_TOKEN):
        return jsonify({
            "success": False,
            "error": "Service authentication required.",
        }), 401

    return None


def rate_limit_error():

    now = time.monotonic()
    client_key = request.remote_addr or "unknown"
    timestamps = queue_requests[client_key]

    while timestamps and now - timestamps[0] >= 60:
        timestamps.popleft()

    if len(timestamps) >= SMS_RATE_LIMIT_PER_MINUTE:
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded. Try again later.",
        }), 429

    timestamps.append(now)
    return None


@app.after_request
def add_cors_headers(response):

    origin = request.headers.get("Origin")
    allowed_origins = [
        value.strip()
        for value in FRONTEND_ORIGINS.split(",")
        if value.strip()
    ]

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Idempotency-Key"
        )
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )

    return response


# =========================================================
# HOME / SERVICE STATUS
# =========================================================

@app.get("/")
def home():

    return jsonify({
        "service": "KarumeSMS",
        "status": "running",
        "sms_provider": "eskiSMS" if "eskisms" in SMS_API_URL.lower() else ("Sakura SMS" if "sakura" in SMS_API_URL.lower() else "SMS Gateway"),
        "sender_id": SMS_SENDER_ID or "NOT CONFIGURED",
        "api_key": (
            "CONFIGURED"
            if SMS_API_KEY
            else "NOT CONFIGURED"
        )
    })


@app.get("/health")
def health():

    return jsonify({
        "success": True,
        "service": "KarumeSMS",
        "status": "healthy",
    })


# =========================================================
# SMS CONFIGURATION TEST
# =========================================================

@app.get("/test/sms")
def test_sms():

    try:

        client = SMSClient()

        return jsonify({
            "success": True,
            "message": "SMS client is configured correctly.",
            "sender": client.sender_id,
            "api_url": client.api_url,
            "api_key": (
                "CONFIGURED"
                if client.api_key
                else "NOT CONFIGURED"
            )
        })

    except Exception as exc:

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# =========================================================
# LIVE SMS TEST
# =========================================================

@app.get("/test/send")
def test_send():

    try:

        client = SMSClient()

        if not TEST_RECIPIENT:
            return jsonify({
                "success": False,
                "error": "TEST_RECIPIENT is not configured.",
            }), 503

        phone = TEST_RECIPIENT

        message = (
            "KarumeSMS test: "
            "SMS integration is working."
        )

        result = client.send_sms(
            phone=phone,
            message=message,
        )

        return jsonify({
            "success": True,
            "message": "SMS submitted successfully.",
            "provider_response": result,
        })

    except Exception as exc:

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500

# =========================================================
# NOTIFICATION API
# =========================================================

@app.post("/notifications/sms")
def queue_notification():

    from notification_service import NotificationService

    rate_error = rate_limit_error()

    if rate_error:
        return rate_error

    auth_error = service_token_error()

    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    idempotency_key = (
        request.headers.get("Idempotency-Key")
        or payload.get("idempotency_key")
    )

    try:

        result = NotificationService().send_sms(
            phone=payload.get("phone"),
            message=payload.get("message"),
            idempotency_key=idempotency_key,
        )

        return jsonify(result), 202

    except (TypeError, ValueError) as exc:

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    except Exception as exc:

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"success": False, "error": "Bad request."}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Resource not found."}), 404


@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({"success": False, "error": "Too many requests."}), 429


@app.errorhandler(500)
def server_error(error):
    return jsonify({"success": False, "error": "Internal server error."}), 500


@app.get("/notifications/sms/<int:sms_id>")
def get_notification_status(sms_id):

    from notification_service import NotificationService

    result = NotificationService().get_sms(sms_id)

    if result is None:
        return jsonify({
            "success": False,
            "error": "SMS not found.",
        }), 404

    return jsonify({
        "success": True,
        "notification": result,
    })


#=================================
#           TEST NOTIFICATION
#=================================

@app.get("/test/notification")
def test_notification():

    from notification_service import NotificationService

    try:

        if not TEST_RECIPIENT:
            return jsonify({
                "success": False,
                "error": "TEST_RECIPIENT is not configured.",
            }), 503

        service = NotificationService()

        result = service.send_sms(
            phone=TEST_RECIPIENT,
            message=(
                "KarumeSMS notification test. "
                "Your notification system is working."
            ),
        )

        return jsonify(result)

    except Exception as exc:

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
    )

