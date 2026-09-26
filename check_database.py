from sqlalchemy.orm import Session

from database.models import (
    SMSMessage,
    engine,
)


with Session(engine) as session:

    messages = (
        session.query(SMSMessage)
        .order_by(SMSMessage.id.desc())
        .all()
    )

    print("\n========== SMS DATABASE ==========\n")

    for sms in messages:

        print(f"ID: {sms.id}")
        print(f"Phone: {sms.phone}")
        print(f"Message: {sms.message}")
        print(f"Sender: {sms.sender}")
        print(f"Status: {sms.status}")
        print(
            f"Provider ID: "
            f"{sms.provider_message_id}"
        )
        print(f"Cost: {sms.cost}")
        print(f"Segments: {sms.segments}")
        print(f"Attempts: {sms.attempts}")
        print(f"Error: {sms.error}")
        print(f"Created: {sms.created_at}")
        print(f"Sent: {sms.sent_at}")
        print(
            f"Max attempts: {sms.max_attempts}"
        )

        print(
            f"Next attempt: {sms.next_attempt_at}"
        )

        print("\n---------------------------------\n")