import re

import requests

from config import (
    SMS_API_KEY,
    SMS_API_URL,
    SMS_SENDER_ID,
)


class SMSClient:

    def __init__(self):

        self.api_key = SMS_API_KEY
        self.api_url = SMS_API_URL
        self.sender_id = SMS_SENDER_ID

    # =====================================================
    # SEND SMS
    # =====================================================

    def send_sms(
        self,
        phone,
        message,
        idempotency_key=None,
    ):

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if phone is None:
            raise ValueError(
                "Phone number is required."
            )

        phone = str(phone).strip().replace(" ", "")

        if phone.startswith("+"):
            phone = phone[1:]

        if phone.startswith("0"):
            phone = "255" + phone[1:]

        if not re.fullmatch(r"255\d{9}", phone):
            raise ValueError(
                "Phone number must be a valid Tanzania number, "
                "for example 255712345678."
            )

        if not message:
            raise ValueError(
                "SMS message is required."
            )

        if not self.api_key:
            raise RuntimeError(
                "SMS_API_KEY is not configured."
            )

        if not self.api_url:
            raise RuntimeError(
                "SMS_API_URL is not configured."
            )

        if not self.sender_id:
            raise RuntimeError(
                "SMS_SENDER_ID is not configured."
            )

        # -------------------------------------------------
        # REQUEST HEADERS
        # -------------------------------------------------

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # -------------------------------------------------
        # REQUEST PAYLOAD
        # -------------------------------------------------

        payload = {
            "recipient": phone,
            "to": phone,
            "sender_id": self.sender_id,
            "sender": self.sender_id,
            "type": "plain",
            "message": message,
        }

        # -------------------------------------------------
        # IDEMPOTENCY KEY
        # -------------------------------------------------

        if idempotency_key:

            payload["idempotency_key"] = (
                idempotency_key
            )

        # -------------------------------------------------
        # SEND REQUEST
        # -------------------------------------------------

        try:

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=15,
            )

        except requests.Timeout as exc:

            raise RuntimeError(
                "SMS provider request timed out."
            ) from exc

        except requests.RequestException as exc:

            raise RuntimeError(
                f"SMS provider connection failed: {exc}"
            ) from exc

        # -------------------------------------------------
        # READ RESPONSE
        # -------------------------------------------------

        try:

            response_data = response.json()

        except ValueError:

            response_data = response.text

        # -------------------------------------------------
        # HANDLE PROVIDER ERROR
        # -------------------------------------------------

        if response.status_code >= 400:

            raise RuntimeError(
                "SMS provider rejected the request "
                f"(HTTP {response.status_code}): "
                f"{response_data}"
            )

        if isinstance(response_data, dict) and response_data.get("status") == "error":

            error_msg = (
                response_data.get("message")
                or response_data.get("error")
                or str(response_data)
            )

            raise RuntimeError(
                f"SMS provider rejected the request: {error_msg}"
            )

        # -------------------------------------------------
        # NORMALIZE PROVIDER RESPONSE
        # -------------------------------------------------

        if isinstance(response_data, dict):

            inner_data = response_data.get("data")

            if isinstance(inner_data, dict):

                if "id" not in response_data:
                    response_data["id"] = (
                        inner_data.get("uid")
                        or inner_data.get("id")
                    )

                if "cost" not in response_data:
                    response_data["cost"] = inner_data.get(
                        "cost"
                    )

                if "segments" not in response_data:
                    response_data["segments"] = (
                        inner_data.get("sms_count")
                        or inner_data.get("segments")
                    )

                if inner_data.get("status"):
                    response_data["status"] = inner_data.get(
                        "status"
                    )

            elif "id" not in response_data and "uid" in response_data:

                response_data["id"] = response_data.get("uid")

        # -------------------------------------------------
        # RETURN PROVIDER RESPONSE
        # -------------------------------------------------

        return response_data