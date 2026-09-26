from sms_worker import SMSWorker


# =====================================================
# FAKE SMS OBJECT
# =====================================================

class FakeSMS:

    id = 999

    phone = "255700000000"

    message = "Retry test"

    idempotency_key = "retry-test-999"

    status = "PENDING"

    attempts = 3

    max_attempts = 3

    provider_message_id = None

    cost = None

    segments = None

    error = None

    sent_at = None

    next_attempt_at = None


# =====================================================
# FAKE SMS CLIENT
# =====================================================

class FakeSMSClient:

    def send_sms(
        self,
        phone,
        message,
        idempotency_key=None,
    ):

        raise RuntimeError(
            "Simulated Sakura connection failure."
        )


# =====================================================
# CREATE WORKER
# =====================================================

worker = SMSWorker()

worker.sms_client = FakeSMSClient()


# =====================================================
# CREATE FAKE SMS
# =====================================================

sms = FakeSMS()


# =====================================================
# PROCESS SMS
# =====================================================

worker.process_sms(sms)


# =====================================================
# SHOW RESULT
# =====================================================

print("\n========== MAX RETRY TEST ==========\n")

print(
    f"Status: {sms.status}"
)

print(
    f"Attempts: {sms.attempts}"
)

print(
    f"Max attempts: {sms.max_attempts}"
)

print(
    f"Error: {sms.error}"
)

print(
    f"Next attempt: {sms.next_attempt_at}"
)

print(
    "\n====================================\n"
)