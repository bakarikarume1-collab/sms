import re
import uuid

from sqlalchemy.orm import Session

from database.models import (
    SMSMessage,
    engine,
)

from sms.client import SMSClient


class NotificationService:

    def __init__(self):

        self.sms_client = SMSClient()

    # =====================================================
    # QUEUE SMS NOTIFICATION
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

        message = str(message).strip()

        if len(message) > 1600:
            raise ValueError(
                "SMS message cannot be longer than 1600 characters."
            )

        if idempotency_key is not None:
            idempotency_key = str(idempotency_key).strip()

            if not idempotency_key or len(idempotency_key) > 100:
                raise ValueError(
                    "Idempotency key must be between 1 and 100 characters."
                )
        else:
            idempotency_key = str(uuid.uuid4())

        # -------------------------------------------------
        # CREATE DATABASE SESSION
        # -------------------------------------------------

        with Session(engine) as session:

            existing_sms = session.query(SMSMessage).filter_by(
                idempotency_key=idempotency_key
            ).first()

            if existing_sms is not None:
                return {
                    "success": True,
                    "sms_id": existing_sms.id,
                    "status": existing_sms.status,
                    "idempotency_key": existing_sms.idempotency_key,
                    "message": "Existing SMS returned for idempotency key.",
                }

            # ---------------------------------------------
            # CREATE PENDING SMS
            # ---------------------------------------------

            sms = SMSMessage(
                idempotency_key=idempotency_key,
                phone=phone,
                message=message,
                sender=self.sms_client.sender_id,
                status="PENDING",
                attempts=0,
            )

            session.add(sms)

            # ---------------------------------------------
            # SAVE TO DATABASE
            # ---------------------------------------------

            session.commit()

            # ---------------------------------------------
            # GET DATABASE ID
            # ---------------------------------------------

            sms_id = sms.id

            # ---------------------------------------------
            # RETURN QUEUED RESPONSE
            # ---------------------------------------------

            return {
                "success": True,
                "sms_id": sms_id,
                "status": "PENDING",
                "idempotency_key": idempotency_key,
                "message": (
                    "SMS added to queue successfully."
                ),
            }

    def get_sms(self, sms_id):

        with Session(engine) as session:

            sms = session.get(SMSMessage, sms_id)

            if sms is None:
                return None

            return {
                "sms_id": sms.id,
                "phone": sms.phone,
                "status": sms.status,
                "attempts": sms.attempts,
                "max_attempts": sms.max_attempts,
                "provider_message_id": sms.provider_message_id,
                "error": sms.error,
                "created_at": (
                    sms.created_at.isoformat()
                    if sms.created_at
                    else None
                ),
                "sent_at": (
                    sms.sent_at.isoformat()
                    if sms.sent_at
                    else None
                ),
            }