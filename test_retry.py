from sms_worker import SMSWorker


# =====================================================
# CREATE WORKER
# =====================================================

worker = SMSWorker()


# =====================================================
# TEST RETRY DELAYS
# =====================================================

print("\n========== RETRY TEST ==========\n")

for attempt in [1, 2, 3, 4]:

    delay = worker.get_retry_delay(
        attempt
    )

    print(
        f"Attempt {attempt} -> "
        f"Retry after {delay} seconds"
    )


print("\n================================\n")