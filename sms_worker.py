import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database.models import (
    Campaign,
    CampaignRecipient,
    SMSMessage,
    engine,
)

from sms.client import SMSClient
from config import WORKER_CLAIM_TIMEOUT_SECONDS


class SMSWorker:

    def __init__(self):

        self.sms_client = SMSClient()

    # =====================================================
    # CALCULATE RETRY DELAY
    # =====================================================

    def get_retry_delay(self, attempts):

        delays = {
            1: 5,
            2: 30,
            3: 120,
        }

        return delays.get(
            attempts,
            120,
        )

    # =====================================================
    # PROCESS ONE SMS
    # =====================================================

    def process_sms(self, sms):

        print(
            f"[WORKER] Processing SMS #{sms.id}"
        )

        sms.status = "PROCESSING"

        try:

            result = self.sms_client.send_sms(
                phone=sms.phone,
                message=sms.message,
                idempotency_key=sms.idempotency_key,
            )

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            provider_status = str(
                result.get("status", "SENT")
            ).upper()

            sms.status = (
                provider_status
                if provider_status in {"SENT", "DELIVERED"}
                else "SENT"
            )

            sms.provider_message_id = result.get(
                "id"
            )

            sms.cost = result.get(
                "cost"
            )

            sms.segments = result.get(
                "segments"
            )

            sms.sent_at = datetime.utcnow()

            sms.error = None

            sms.next_attempt_at = None

            sms.claimed_at = None

            print(
                f"[WORKER] SMS #{sms.id} sent successfully."
            )

        except Exception as exc:

            # -------------------------------------------------
            # SAVE ERROR
            # -------------------------------------------------

            sms.error = str(exc)

            # -------------------------------------------------
            # CHECK RETRY LIMIT
            # -------------------------------------------------

            if sms.attempts >= sms.max_attempts:

                sms.status = "PERMANENTLY_FAILED"

                sms.next_attempt_at = None

                sms.claimed_at = None

                print(
                    f"[WORKER] SMS #{sms.id} "
                    f"permanently failed after "
                    f"{sms.attempts} attempts."
                )

                return

            # -------------------------------------------------
            # CALCULATE BACKOFF
            # -------------------------------------------------

            delay_seconds = self.get_retry_delay(
                sms.attempts
            )

            sms.status = "RETRY"

            sms.claimed_at = None

            sms.next_attempt_at = (
                datetime.utcnow()
                + timedelta(
                    seconds=delay_seconds
                )
            )

            print(
                f"[WORKER] SMS #{sms.id} failed."
            )

            print(
                f"[WORKER] Retry scheduled in "
                f"{delay_seconds} seconds."
            )

    def sync_campaign_state(self, session, sms):

        recipient = session.query(CampaignRecipient).filter_by(
            sms_message_id=sms.id
        ).first()

        if recipient is None:
            return

        if sms.status in {"SENT", "DELIVERED"}:
            recipient.status = sms.status
            recipient.provider_message_id = sms.provider_message_id
            recipient.sent_at = sms.sent_at
            recipient.error = None
        elif sms.status == "PERMANENTLY_FAILED":
            recipient.status = "FAILED"
            recipient.error = sms.error
        else:
            recipient.status = sms.status
            recipient.error = sms.error

        campaign = session.get(Campaign, recipient.campaign_id)

        if campaign is None:
            return

        recipients = session.query(CampaignRecipient).filter_by(
            campaign_id=campaign.id
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

    # =====================================================
    # PROCESS QUEUE
    # =====================================================

    def process_queue(self):

        with Session(engine) as session:

            now = datetime.utcnow()
            claim_expired_at = (
                now
                - timedelta(
                    seconds=WORKER_CLAIM_TIMEOUT_SECONDS
                )
            )

            # Recover messages claimed by a worker that stopped unexpectedly.
            session.query(SMSMessage).filter(
                SMSMessage.status == "PROCESSING",
                SMSMessage.claimed_at <= claim_expired_at,
            ).update(
                {
                    SMSMessage.status: "RETRY",
                    SMSMessage.claimed_at: None,
                    SMSMessage.next_attempt_at: now,
                },
                synchronize_session=False,
            )
            session.commit()

            # -------------------------------------------------
            # FIND AVAILABLE SMS
            # -------------------------------------------------

            sms = (
                session.query(SMSMessage)
                .filter(
                    SMSMessage.status.in_(
                        [
                            "PENDING",
                            "RETRY",
                        ]
                    )
                )
                .filter(
                    (
                        SMSMessage.next_attempt_at.is_(None)
                    )
                    |
                    (
                        SMSMessage.next_attempt_at <= now
                    )
                )
                .filter(
                    SMSMessage.claimed_at.is_(None)
                )
                .order_by(
                    SMSMessage.id.asc()
                )
                .first()
            )

            if not sms:

                return False

            # -------------------------------------------------
            # CLAIM SMS
            # -------------------------------------------------

            sms.status = "PROCESSING"

            sms.claimed_at = now

            sms.attempts += 1

            session.commit()

            # -------------------------------------------------
            # PROCESS SMS
            # -------------------------------------------------

            try:

                self.process_sms(sms)

                self.sync_campaign_state(session, sms)

                session.commit()

            except Exception as exc:

                session.rollback()

                print(
                    f"[WORKER] Queue processing error: {exc}"
                )

            return True

    # =====================================================
    # START WORKER
    # =====================================================

    def run(self):

        print(
            "[WORKER] KarumeSMS worker started."
        )

        while True:

            processed = self.process_queue()

            if not processed:

                time.sleep(2)


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if __name__ == "__main__":

    worker = SMSWorker()

    worker.run()