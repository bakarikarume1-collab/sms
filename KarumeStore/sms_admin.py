import os

import requests

from flask import Blueprint, jsonify, request

from auth import admin_required


sms_admin = Blueprint("sms_admin", __name__)

SMS_SERVICE_URL = os.environ.get(
    "SMS_SERVICE_URL",
    "http://127.0.0.1:5001",
).rstrip("/")
SMS_ADMIN_TOKEN = os.environ.get("SMS_ADMIN_TOKEN", "")


def forward(path, method="GET", **kwargs):

    if not SMS_ADMIN_TOKEN:
        return jsonify({
            "success": False,
            "message": "SMS_ADMIN_TOKEN is not configured."
        }), 503

    try:
        response = requests.request(
            method,
            f"{SMS_SERVICE_URL}{path}",
            headers={"X-Admin-Token": SMS_ADMIN_TOKEN},
            timeout=10,
            **kwargs,
        )
        return jsonify(response.json()), response.status_code
    except (requests.RequestException, ValueError) as exc:
        return jsonify({
            "success": False,
            "message": f"SMS service unavailable: {exc}",
        }), 503


@sms_admin.get("/api/admin/sms/dashboard")
@admin_required
def dashboard():
    return forward("/api/dashboard/sms")


@sms_admin.get("/api/admin/sms/contacts")
@admin_required
def contacts():
    query = request.query_string.decode("utf-8")
    return forward(f"/api/contacts?{query}" if query else "/api/contacts")


@sms_admin.post("/api/admin/sms/contacts")
@admin_required
def create_contact():
    return forward(
        "/api/contacts",
        "POST",
        json=request.get_json(silent=True) or {},
    )


@sms_admin.post("/api/admin/sms/campaigns")
@admin_required
def create_campaign():
    return forward(
        "/api/campaigns",
        "POST",
        json=request.get_json(silent=True) or {},
    )


@sms_admin.get("/api/admin/sms/campaigns")
@admin_required
def list_campaigns():
    return forward("/api/campaigns")


@sms_admin.post("/api/admin/sms/campaigns/<int:campaign_id>/send")
@admin_required
def send_campaign(campaign_id):
    return forward(
        f"/api/campaigns/{campaign_id}/send",
        "POST",
    )


@sms_admin.post("/api/admin/sms/contacts/import")
@admin_required
def import_contacts():

    upload = request.files.get("file")

    if not upload:
        return jsonify({
            "success": False,
            "message": "A CSV file is required."
        }), 400

    return forward(
        "/api/contacts/import",
        "POST",
        files={
            "file": (
                upload.filename,
                upload.stream,
                upload.mimetype,
            )
        },
        data={"group_id": request.form.get("group_id", "")},
    )