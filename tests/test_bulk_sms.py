from types import SimpleNamespace

from bulk_api import normalize_phone, segments_for
from sms.client import SMSClient


def test_normalize_tanzania_phone_formats():

    assert normalize_phone("0743771438") == "255743771438"
    assert normalize_phone("+255743771438") == "255743771438"
    assert normalize_phone("255743771438") == "255743771438"


def test_reject_invalid_phone():

    try:
        normalize_phone("12345")
    except ValueError as exc:
        assert "valid Tanzania" in str(exc)
    else:
        raise AssertionError("Invalid phone was accepted")


def test_sms_segment_calculation():

    assert segments_for("a" * 160) == 1
    assert segments_for("a" * 161) == 2
    assert segments_for("a" * 306) == 2
    assert segments_for("a" * 307) == 3


def test_sms_client_normalizes_provider_payload(monkeypatch):

    client = SMSClient()
    client.api_key = "test-key"
    client.api_url = "https://provider.invalid/messages"
    client.sender_id = "TEST"
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured.update(json)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"status": "SENT", "id": "provider-1"},
            text="",
        )

    monkeypatch.setattr("sms.client.requests.post", fake_post)

    result = client.send_sms(
        phone="0712345678",
        message="Test message",
        idempotency_key="test-idempotency",
    )

    assert result["id"] == "provider-1"
    assert captured["to"] == "255712345678"
    assert captured["recipient"] == "255712345678"
    assert captured["sender_id"] == "TEST"
    assert captured["type"] == "plain"
    assert captured["idempotency_key"] == "test-idempotency"


def test_sms_client_handles_eskisms_response(monkeypatch):

    client = SMSClient()
    client.api_key = "test-key"
    client.api_url = "https://eskisms.com/api/v3/sms/send"
    client.sender_id = "HARUSI"

    def fake_post(url, json, headers, timeout):
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "success",
                "message": "Your message was successfully delivered",
                "data": {
                    "uid": "6aae3f90bfc8c",
                    "to": "255743771438",
                    "from": "HARUSI",
                    "message": "Test",
                    "status": "Delivered",
                    "cost": "1",
                    "sms_count": 1,
                },
            },
            text="",
        )

    monkeypatch.setattr("sms.client.requests.post", fake_post)

    result = client.send_sms(
        phone="0743771438",
        message="Test message",
    )

    assert result["id"] == "6aae3f90bfc8c"
    assert result["status"] == "Delivered"
    assert result["cost"] == "1"
    assert result["segments"] == 1


def test_sms_client_raises_on_eskisms_error(monkeypatch):

    client = SMSClient()
    client.api_key = "test-key"
    client.api_url = "https://eskisms.com/api/v3/sms/send"
    client.sender_id = "HARUSI"

    def fake_post(url, json, headers, timeout):
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "status": "error",
                "message": "The recipient field is required.",
            },
            text="",
        )

    monkeypatch.setattr("sms.client.requests.post", fake_post)

    try:
        client.send_sms(
            phone="0743771438",
            message="Test message",
        )
    except RuntimeError as exc:
        assert "recipient field is required" in str(exc)
    else:
        raise AssertionError("Expected error was not raised")
