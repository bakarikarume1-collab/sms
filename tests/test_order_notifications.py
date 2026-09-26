import os
import sys
from types import SimpleNamespace

# Ensure KarumeStore is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "KarumeStore"))

from sms_service import queue_new_order_admin_sms, queue_order_status_customer_sms


def test_queue_new_order_admin_sms(monkeypatch):

    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"success": True, "sms_id": 99, "status": "PENDING"},
        )

    monkeypatch.setattr("sms_service.requests.post", fake_post)
    monkeypatch.setenv("ADMIN_PHONE", "255743771438")

    result = queue_new_order_admin_sms(
        order_id=42,
        order_number="ORD-2026-0042",
        total=150000,
        customer_name="Amina Juma",
        customer_phone="0712345678",
    )

    assert result["success"] is True
    assert captured["headers"]["Idempotency-Key"] == "order-42-admin-alert"
    assert captured["json"]["phone"] == "255743771438"
    assert "ORD-2026-0042" in captured["json"]["message"]
    assert "Amina Juma" in captured["json"]["message"]
    assert "150,000" in captured["json"]["message"]


def test_queue_order_status_customer_sms(monkeypatch):

    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"success": True, "sms_id": 100, "status": "PENDING"},
        )

    monkeypatch.setattr("sms_service.requests.post", fake_post)

    result = queue_order_status_customer_sms(
        order_id=42,
        order_number="ORD-2026-0042",
        phone="0712345678",
        new_status="OUT_FOR_DELIVERY",
        customer_name="Amina Juma",
    )

    assert result["success"] is True
    assert captured["headers"]["Idempotency-Key"] == "order-42-status-out_for_delivery"
    assert captured["json"]["phone"] == "0712345678"
    assert "ORD-2026-0042" in captured["json"]["message"]
    assert "Amina Juma" in captured["json"]["message"]
    assert "njiani inakujia" in captured["json"]["message"]

