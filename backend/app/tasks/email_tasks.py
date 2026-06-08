import time
from datetime import datetime
from uuid import UUID
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Trader, Campaign, EmailLog, EmailStatus
from app.services.email_service import send_email
from app.config import settings


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_to_trader(self, trader_id: str, campaign_id: str | None = None):
    db = SessionLocal()
    try:
        trader = db.query(Trader).filter(Trader.id == UUID(trader_id)).first()
        if not trader or not trader.email:
            return {"skipped": True, "reason": "no email"}

        result = send_email(trader.email, trader.company_name)

        log = EmailLog(
            trader_id=trader.id,
            campaign_id=UUID(campaign_id) if campaign_id else None,
            status=EmailStatus.sent if result["success"] else EmailStatus.bounced,
            sendgrid_message_id=result.get("message_id"),
            error_message=result.get("error"),
        )
        db.add(log)

        trader.email_status = EmailStatus.sent if result["success"] else EmailStatus.bounced
        if result["success"]:
            trader.sent_at = datetime.utcnow()

        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task
def run_campaign(campaign_id: str):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == UUID(campaign_id)).first()
        if not campaign:
            return

        campaign.status = "running"
        db.commit()

        traders = (
            db.query(Trader)
            .filter(Trader.approved == True, Trader.email_valid == True)
            .filter(Trader.email_status == EmailStatus.pending)
            .all()
        )

        delay_seconds = 60 / max(settings.email_throttle_per_minute, 1)

        for trader in traders:
            send_email_to_trader.delay(str(trader.id), campaign_id)
            time.sleep(delay_seconds)

        campaign.status = "done"
        campaign.finished_at = datetime.utcnow()
        campaign.total_traders = str(len(traders))
        db.commit()
    finally:
        db.close()
