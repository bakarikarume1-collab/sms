import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Index,
    UniqueConstraint,
)

from sqlalchemy.orm import declarative_base


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///karumesms.db"

DATABASE_URL = DATABASE_URL.replace(
    "postgres://",
    "postgresql://",
    1,
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


Base = declarative_base()


# =========================================================
# SMS MESSAGE
# =========================================================

class SMSMessage(Base):

    __tablename__ = "sms_messages"

    id = Column(
        Integer,
        primary_key=True,
    )
    idempotency_key = Column(
    String(100),
    nullable=False,
    unique=True,

    )

    # -----------------------------------------------------
    # RECIPIENT
    # -----------------------------------------------------

    phone = Column(
        String(30),
        nullable=False,
    )

    # -----------------------------------------------------
    # MESSAGE
    # -----------------------------------------------------

    message = Column(
        Text,
        nullable=False,
    )

    # -----------------------------------------------------
    # SENDER
    # -----------------------------------------------------

    sender = Column(
        String(20),
        nullable=False,
    )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    status = Column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    # -----------------------------------------------------
    # PROVIDER MESSAGE ID
    # -----------------------------------------------------

    provider_message_id = Column(
        String(100),
        nullable=True,
    )

    # -----------------------------------------------------
    # PROVIDER COST
    # -----------------------------------------------------

    cost = Column(
        Float,
        nullable=True,
    )

    # -----------------------------------------------------
    # SMS SEGMENTS
    # -----------------------------------------------------

    segments = Column(
        Integer,
        nullable=True,
    )

    # -----------------------------------------------------
    # NUMBER OF ATTEMPTS OF SENDING MESSAGE
    # -----------------------------------------------------
    attempts = Column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts = Column(
        Integer,
        nullable=False,
        default=3,
    )

    next_attempt_at = Column(
        DateTime,
        nullable=True,
    )

    claimed_at = Column(
        DateTime,
        nullable=True,
    )

    error = Column(
        Text,
        nullable=True,
    )
    # -----------------------------------------------------
    # CREATED
    # -----------------------------------------------------

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    # -----------------------------------------------------
    # SENT
    # -----------------------------------------------------

    sent_at = Column(
        DateTime,
        nullable=True,
    )


class ContactGroup(Base):

    __tablename__ = "contact_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Contact(Base):

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(160), nullable=False)
    phone = Column(String(30), nullable=False)
    email = Column(String(255), nullable=True)
    group_id = Column(
        Integer,
        ForeignKey("contact_groups.id"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "phone",
            "group_id",
            name="uq_contact_phone_group",
        ),
        Index("ix_contacts_phone", "phone"),
        Index("ix_contacts_status", "status"),
    )


class Campaign(Base):

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    sender = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default="DRAFT")
    recipient_count = Column(Integer, nullable=False, default=0)
    sms_count = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    pending_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class CampaignRecipient(Base):

    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id"),
        nullable=False,
    )
    contact_id = Column(
        Integer,
        ForeignKey("contacts.id"),
        nullable=True,
    )
    phone = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    sms_message_id = Column(
        Integer,
        ForeignKey("sms_messages.id"),
        nullable=True,
    )
    provider_message_id = Column(String(100), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "phone",
            name="uq_campaign_recipient_phone",
        ),
        Index("ix_campaign_recipient_status", "status"),
    )


class DeliveryEvent(Base):

    __tablename__ = "delivery_events"

    id = Column(Integer, primary_key=True)
    event_key = Column(String(180), nullable=False, unique=True)
    provider_message_id = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# =========================================================
# CREATE DATABASE
# =========================================================

def create_tables():

    Base.metadata.create_all(
        engine
    )


if __name__ == "__main__":

    create_tables()

    print(
        "KarumeSMS database initialized successfully."
    )

