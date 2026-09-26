import csv
import io
import json
import re
import secrets
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import SMS_ADMIN_TOKEN, SMS_SENDER_ID, SMS_WEBHOOK_SECRET
from database.models import (
    Campaign,
    CampaignRecipient,
    Contact,
    ContactGroup,
    DeliveryEvent,
    SMSMessage,
    engine,
)
from notification_service import NotificationService


bulk = Blueprint("bulk", __name__)


def require_admin_token():

    if not SMS_ADMIN_TOKEN:
        return jsonify({
            "success": False,
            "error": "SMS_ADMIN_TOKEN is not configured.",
        }), 503

    provided = request.headers.get("X-Admin-Token", "")

    if not secrets.compare_digest(provided, SMS_ADMIN_TOKEN):
        return jsonify({
            "success": False,
            "error": "Admin authentication required.",
        }), 401

    return None


def normalize_phone(phone):

    value = str(phone or "").strip().replace(" ", "")

    if value.startswith("+"):
        value = value[1:]

    if value.startswith("0"):
        value = "255" + value[1:]

    if not re.fullmatch(r"255\d{9}", value):
        raise ValueError(
            "Phone number must be a valid Tanzania number."
        )

    return value


def segments_for(message):

    length = len(message)

    if length <= 160:
        return 1

    return (length + 152) // 153


def contact_dict(contact):

    return {
        "id": contact.id,
        "full_name": contact.full_name,
        "phone": contact.phone,
        "email": contact.email,
        "group_id": contact.group_id,
        "status": contact.status,
        "created_at": contact.created_at.isoformat(),
        "updated_at": contact.updated_at.isoformat(),
    }


def campaign_dict(campaign):

    return {
        "id": campaign.id,
        "name": campaign.name,
        "message": campaign.message,
        "sender": campaign.sender,
        "status": campaign.status,
        "recipient_count": campaign.recipient_count,
        "sms_count": campaign.sms_count,
        "sent_count": campaign.sent_count,
        "failed_count": campaign.failed_count,
        "pending_count": campaign.pending_count,
        "created_at": campaign.created_at.isoformat(),
        "sent_at": campaign.sent_at.isoformat()
        if campaign.sent_at else None,
        "completed_at": campaign.completed_at.isoformat()
        if campaign.completed_at else None,
    }


def refresh_campaign_stats(session, campaign_id):

    campaign = session.get(Campaign, campaign_id)

    if campaign is None:
        return

    recipients = session.query(CampaignRecipient).filter_by(
        campaign_id=campaign_id
    ).all()
    sent_count = sum(
        item.status in {"SENT", "DELIVERED"}
        for item in recipients
    )
    failed_count = sum(
        item.status in {"FAILED", "REJECTED"}
        for item in recipients
    )
    pending_count = sum(
        item.status not in {"SENT", "DELIVERED", "FAILED", "REJECTED"}
        for item in recipients
    )

    campaign.sent_count = sent_count
    campaign.failed_count = failed_count
    campaign.pending_count = pending_count

    if pending_count:
        campaign.status = "SENDING"
    elif failed_count and sent_count:
        campaign.status = "PARTIAL"
        campaign.completed_at = datetime.utcnow()
    elif failed_count:
        campaign.status = "FAILED"
        campaign.completed_at = datetime.utcnow()
    else:
        campaign.status = "COMPLETED"
        campaign.completed_at = datetime.utcnow()


@bulk.get("/api/contacts")
def list_contacts():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    with Session(engine) as session:
        query = session.query(Contact).order_by(Contact.id.desc())
        group_id = request.args.get("group_id")
        search = request.args.get("search", "").strip()

        if group_id:
            query = query.filter(Contact.group_id == int(group_id))

        if search:
            query = query.filter(
                (Contact.full_name.ilike(f"%{search}%"))
                | (Contact.phone.ilike(f"%{search}%"))
            )

        return jsonify({
            "success": True,
            "contacts": [contact_dict(item) for item in query.all()],
        })


@bulk.post("/api/contacts")
def create_contact():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}

    try:
        full_name = str(data.get("full_name", "")).strip()
        phone = normalize_phone(data.get("phone"))
        email = str(data.get("email", "")).strip() or None
        group_id = data.get("group_id")

        if not full_name:
            raise ValueError("Full name is required.")

        with Session(engine) as session:
            contact = Contact(
                full_name=full_name,
                phone=phone,
                email=email,
                group_id=group_id,
            )
            session.add(contact)
            session.commit()
            return jsonify({
                "success": True,
                "contact": contact_dict(contact),
            }), 201

    except (ValueError, IntegrityError) as exc:
        return jsonify({
            "success": False,
            "error": (
                "Duplicate contact or invalid data."
                if isinstance(exc, IntegrityError)
                else str(exc)
            ),
        }), 400


@bulk.patch("/api/contacts/<int:contact_id>")
def update_contact(contact_id):

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}

    with Session(engine) as session:
        contact = session.get(Contact, contact_id)

        if contact is None:
            return jsonify({
                "success": False,
                "error": "Contact not found.",
            }), 404

        try:
            if "full_name" in data:
                contact.full_name = str(data["full_name"]).strip()
                if not contact.full_name:
                    raise ValueError("Full name is required.")

            if "phone" in data:
                contact.phone = normalize_phone(data["phone"])

            if "email" in data:
                contact.email = str(data["email"]).strip() or None

            if "group_id" in data:
                contact.group_id = data["group_id"]

            if "status" in data:
                status = str(data["status"]).upper()
                if status not in {"ACTIVE", "INACTIVE"}:
                    raise ValueError("Contact status is invalid.")
                contact.status = status

            session.commit()

        except (ValueError, IntegrityError) as exc:
            session.rollback()
            return jsonify({
                "success": False,
                "error": (
                    "Duplicate contact or invalid data."
                    if isinstance(exc, IntegrityError)
                    else str(exc)
                ),
            }), 400

        return jsonify({
            "success": True,
            "contact": contact_dict(contact),
        })


@bulk.delete("/api/contacts/<int:contact_id>")
def delete_contact(contact_id):

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    with Session(engine) as session:
        contact = session.get(Contact, contact_id)

        if contact is None:
            return jsonify({
                "success": False,
                "error": "Contact not found.",
            }), 404

        session.delete(contact)
        session.commit()

    return jsonify({"success": True})


@bulk.post("/api/contact-groups")
def create_group():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()

    if not name or len(name) > 120:
        return jsonify({
            "success": False,
            "error": "Group name is required and must be 120 characters or fewer.",
        }), 400

    with Session(engine) as session:
        group = ContactGroup(name=name)
        session.add(group)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return jsonify({
                "success": False,
                "error": "A group with this name already exists.",
            }), 409

        return jsonify({
            "success": True,
            "group": {
                "id": group.id,
                "name": group.name,
            },
        }), 201


@bulk.post("/api/contacts/import")
def import_contacts():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    upload = request.files.get("file")

    if not upload or not upload.filename.lower().endswith(".csv"):
        return jsonify({
            "success": False,
            "error": "A CSV file is required.",
        }), 400

    raw = upload.read(2_000_001)

    if len(raw) > 2_000_000:
        return jsonify({
            "success": False,
            "error": "CSV file cannot exceed 2 MB.",
        }), 413

    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"full_name", "phone"}

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain full_name and phone columns.")

        group_id = request.form.get("group_id") or None
        created = 0
        skipped = 0

        with Session(engine) as session:
            for row in reader:
                try:
                    phone = normalize_phone(row.get("phone"))
                    full_name = str(row.get("full_name", "")).strip()

                    if not full_name:
                        skipped += 1
                        continue

                    exists = session.query(Contact).filter_by(
                        phone=phone,
                        group_id=group_id,
                    ).first()

                    if exists:
                        skipped += 1
                        continue

                    session.add(Contact(
                        full_name=full_name,
                        phone=phone,
                        email=str(row.get("email", "")).strip() or None,
                        group_id=group_id,
                    ))
                    created += 1

                except ValueError:
                    skipped += 1

            session.commit()

        return jsonify({
            "success": True,
            "created": created,
            "skipped": skipped,
        }), 201

    except (UnicodeDecodeError, ValueError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


@bulk.post("/api/campaigns")
def create_campaign():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    message = str(data.get("message", "")).strip()
    contact_ids = data.get("contact_ids") or []
    group_id = data.get("group_id")

    if not name or not message:
        return jsonify({
            "success": False,
            "error": "Campaign name and message are required.",
        }), 400

    if len(message) > 1600:
        return jsonify({
            "success": False,
            "error": "Message cannot exceed 1600 characters.",
        }), 400

    with Session(engine) as session:
        query = session.query(Contact).filter(Contact.status == "ACTIVE")

        if contact_ids:
            query = query.filter(Contact.id.in_(contact_ids))
        elif group_id:
            query = query.filter(Contact.group_id == group_id)
        else:
            return jsonify({
                "success": False,
                "error": "Select contacts or a contact group.",
            }), 400

        contacts = query.all()

        if not contacts:
            return jsonify({
                "success": False,
                "error": "No active contacts were selected.",
            }), 400

        campaign = Campaign(
            name=name,
            message=message,
            sender=SMS_SENDER_ID,
            recipient_count=len(contacts),
            sms_count=len(contacts) * segments_for(message),
        )
        session.add(campaign)
        session.flush()

        for contact in contacts:
            session.add(CampaignRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                phone=contact.phone,
            ))

        session.commit()

        return jsonify({
            "success": True,
            "campaign": campaign_dict(campaign),
            "segments_per_recipient": segments_for(message),
        }), 201


@bulk.get("/api/campaigns")
def list_campaigns():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    with Session(engine) as session:
        campaigns = session.query(Campaign).order_by(
            Campaign.id.desc()
        ).all()
        return jsonify({
            "success": True,
            "campaigns": [campaign_dict(item) for item in campaigns],
        })


@bulk.post("/api/campaigns/<int:campaign_id>/send")
def send_campaign(campaign_id):

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    with Session(engine) as session:
        campaign = session.get(Campaign, campaign_id)

        if not campaign:
            return jsonify({
                "success": False,
                "error": "Campaign not found.",
            }), 404

        if campaign.status not in {"DRAFT", "FAILED"}:
            return jsonify({
                "success": False,
                "error": "Campaign has already been queued.",
            }), 409

        recipients = session.query(CampaignRecipient).filter_by(
            campaign_id=campaign.id,
            status="PENDING",
        ).all()

        if not recipients:
            return jsonify({
                "success": False,
                "error": "Campaign has no pending recipients.",
            }), 400

        service = NotificationService()
        queued = 0
        failed = 0

        campaign.status = "QUEUED"
        campaign.sent_at = datetime.utcnow()

        for recipient in recipients:
            key = f"campaign-{campaign.id}-recipient-{recipient.id}"

            try:
                result = service.send_sms(
                    phone=recipient.phone,
                    message=campaign.message,
                    idempotency_key=key,
                )
                recipient.sms_message_id = result.get("sms_id")
                recipient.status = "QUEUED"
                queued += 1
            except Exception as exc:
                recipient.status = "FAILED"
                recipient.error = str(exc)
                failed += 1

        campaign.pending_count = queued
        campaign.failed_count = failed
        campaign.status = "QUEUED" if queued else "FAILED"
        session.commit()

        return jsonify({
            "success": True,
            "queued": queued,
            "failed": failed,
            "campaign": campaign_dict(campaign),
        }), 202


@bulk.get("/api/dashboard/sms")
def sms_dashboard():

    auth_error = require_admin_token()

    if auth_error:
        return auth_error

    with Session(engine) as session:
        today = datetime.utcnow().date()
        return jsonify({
            "success": True,
            "total_contacts": session.query(Contact).count(),
            "total_campaigns": session.query(Campaign).count(),
            "total_sms": session.query(SMSMessage).count(),
            "sent_sms": session.query(SMSMessage).filter(
                SMSMessage.status.in_(["SENT", "DELIVERED"])
            ).count(),
            "failed_sms": session.query(SMSMessage).filter(
                SMSMessage.status.in_([
                    "FAILED",
                    "PERMANENTLY_FAILED",
                ])
            ).count(),
            "pending_sms": session.query(SMSMessage).filter(
                SMSMessage.status.in_(["PENDING", "RETRY", "PROCESSING"])
            ).count(),
            "today_sms": session.query(SMSMessage).filter(
                func.date(SMSMessage.created_at) == today
            ).count(),
        })


@bulk.post("/api/webhooks/sakura")
def sakura_webhook():

    if not SMS_WEBHOOK_SECRET:
        return jsonify({
            "success": False,
            "error": "Webhook secret is not configured.",
        }), 503

    provided = request.headers.get("X-Webhook-Secret", "")

    if not secrets.compare_digest(provided, SMS_WEBHOOK_SECRET):
        return jsonify({
            "success": False,
            "error": "Invalid webhook credentials.",
        }), 401

    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "UNKNOWN")).upper()
    provider_id = str(
        payload.get("message_id")
        or payload.get("id")
        or ""
    ).strip()
    event_key = str(
        payload.get("event_id")
        or f"{provider_id}:{status}:{payload.get('timestamp', '')}"
    )

    if status not in {"SENT", "DELIVERED", "FAILED", "REJECTED", "UNKNOWN"}:
        return jsonify({
            "success": False,
            "error": "Unsupported delivery status.",
        }), 400

    with Session(engine) as session:
        if session.query(DeliveryEvent).filter_by(event_key=event_key).first():
            return jsonify({"success": True, "duplicate": True})

        session.add(DeliveryEvent(
            event_key=event_key,
            provider_message_id=provider_id or None,
            status=status,
            payload=json.dumps(payload),
        ))

        recipient = None

        if provider_id:
            recipient = session.query(CampaignRecipient).filter_by(
                provider_message_id=provider_id
            ).first()

        if recipient:
            recipient.status = status
            recipient.provider_message_id = provider_id
            recipient.sent_at = datetime.utcnow()
            refresh_campaign_stats(session, recipient.campaign_id)

        session.commit()

    return jsonify({"success": True}), 200