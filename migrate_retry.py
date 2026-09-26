from sqlalchemy import text

from database.models import engine


# =====================================================
# ADD CLAIM COLUMN
# =====================================================

with engine.begin() as connection:

    connection.execute(
        text(
            """
            ALTER TABLE sms_messages
            ADD COLUMN claimed_at DATETIME
            """
        )
    )


print(
    "Claim column added successfully."
)