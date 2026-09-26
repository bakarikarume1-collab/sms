import os

from dotenv import load_dotenv


load_dotenv()


SMS_API_KEY = os.getenv(
    "SMS_API_KEY",
    os.getenv("SAKURA_API_KEY", "")
).strip().strip("'\"")

SMS_API_URL = os.getenv(
    "SMS_API_URL",
    os.getenv("SAKURA_BASE_URL", "")
).strip().strip("'\"")

SMS_SENDER_ID = os.getenv(
    "SMS_SENDER_ID",
    os.getenv("SAKURA_SENDER", "")
).strip().strip("'\"")

SMS_ADMIN_TOKEN = os.getenv(
    "SMS_ADMIN_TOKEN",
    "",
)

SMS_SERVICE_TOKEN = os.getenv(
    "SMS_SERVICE_TOKEN",
    "",
)

SMS_WEBHOOK_SECRET = os.getenv(
    "SMS_WEBHOOK_SECRET",
    os.getenv("SAKURA_WEBHOOK_SECRET", ""),
)

TEST_RECIPIENT = os.getenv(
    "TEST_RECIPIENT",
    "",
)

FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)

WORKER_CLAIM_TIMEOUT_SECONDS = int(
    os.getenv(
        "WORKER_CLAIM_TIMEOUT_SECONDS",
        "600",
    )
)

SMS_RATE_LIMIT_PER_MINUTE = int(
    os.getenv(
        "SMS_RATE_LIMIT_PER_MINUTE",
        "60",
    )
)