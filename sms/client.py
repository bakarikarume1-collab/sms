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
    # NORMALIZE TANZANIA PHONE NUMBER
    # =====================================================

    def normalize_phone(self, phone):

        if phone is None:
            raise ValueError(
                "Phone number is required."
            )

        phone = (
            str(phone)
            .strip()
            .replace(" ", "")
            .replace("-", "")
        )

        if phone.startswith("+"):
            phone = phone[1:]

        if phone.startswith("0"):
            phone = "255" + phone[1:]

        if not re.fullmatch(r"255\d{9}", phone):
            raise ValueError(
                "Phone number must be a valid Tanzania number, "
                "for example 255712345678."
            )

        return phone

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

        phone = self.normalize_phone(phone)

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
        # HEADERS
        # -------------------------------------------------

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # -------------------------------------------------
        # ESKI SMS PAYLOAD
        # -------------------------------------------------

        payload = {
            "recipient": phone,
            "sender_id": self.sender_id,
            "type": "plain",
            "message": message,
        }

        # -------------------------------------------------
        # DEBUG INFO
        # -------------------------------------------------

        print(
            f"[SMS] Sending SMS to {phone}"
        )

        print(
            f"[SMS] Endpoint: {self.api_url}"
        )

        print(
            f"[SMS] Sender ID: {self.sender_id}"
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

            response_data = {
                "status": "error",
                "message": response.text,
            }

        print(
            f"[SMS] HTTP status: {response.status_code}"
        )

        print(
            f"[SMS] Provider response: {response_data}"
        )

        # -------------------------------------------------
        # HTTP ERROR
        # -------------------------------------------------

        if response.status_code >= 400:

            if isinstance(response_data, dict):

                error_message = (
                    response_data.get("message")
                    or response_data.get("error")
                    or str(response_data)
                )

            else:

                error_message = str(response_data)

            raise RuntimeError(
                "SMS provider rejected the request "
                f"(HTTP {response.status_code}): "
                f"{error_message}"
            )

        # -------------------------------------------------
        # ESKI APPLICATION ERROR
        # -------------------------------------------------

        if isinstance(response_data, dict):

            provider_status = str(
                response_data.get(
                    "status",
                    ""
                )
            ).lower()

            if provider_status == "error":

                error_message = (
                    response_data.get("message")
                    or response_data.get("error")
                    or "Unknown SMS provider error."
                )

                raise RuntimeError(
                    "SMS provider rejected the request: "
                    f"{error_message}"
                )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if not isinstance(response_data, dict):

            raise RuntimeError(
                "SMS provider returned an invalid response."
            )

        provider_status = str(
            response_data.get(
                "status",
                ""
            )
        ).lower()

        if provider_status != "success":

            raise RuntimeError(
                "SMS provider returned an unexpected response: "
                f"{response_data}"
            )

        # -------------------------------------------------
        # EXTRACT DATA
        # -------------------------------------------------

        data = response_data.get("data")

        # Eski documentation shows data containing
        # SMS report details. Different API responses
        # may return this as a dictionary or list.

        if isinstance(data, dict):

            provider_id = (
                data.get("uid")
                or data.get("id")
            )

            cost = data.get("cost")

            segments = (
                data.get("sms_count")
                or data.get("segments")
            )

            status = data.get(
                "status",
                "SENT"
            )

        elif isinstance(data, list) and data:

            first_item = data[0]

            if isinstance(first_item, dict):

                provider_id = (
                    first_item.get("uid")
                    or first_item.get("id")
                )

                cost = first_item.get("cost")

                segments = (
                    first_item.get("sms_count")
                    or first_item.get("segments")
                )

                status = first_item.get(
                    "status",
                    "SENT"
                )

            else:

                provider_id = None
                cost = None
                segments = None
                status = "SENT"

        else:

            provider_id = None
            cost = None
            segments = None
            status = "SENT"

        # -------------------------------------------------
        # NORMALIZED RESPONSE
        # -------------------------------------------------

        normalized = {
            "status": str(
                status or "SENT"
            ).upper(),

            "id": provider_id,

            "cost": cost,

            "segments": segments,

            "raw_response": response_data,
        }

        print(
            "[SMS] SMS accepted successfully."
        )

        print(
            f"[SMS] Provider ID: {provider_id}"
        )

        return normalized
