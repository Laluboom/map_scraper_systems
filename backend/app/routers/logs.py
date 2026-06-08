from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EmailLog
from app.schemas import EmailLogOut

router = APIRouter()


@router.get("/", response_model=List[EmailLogOut])
def list_logs(
    campaign_id: Optional[UUID] = None,
    trader_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(EmailLog)
    if campaign_id:
        q = q.filter(EmailLog.campaign_id == campaign_id)
    if trader_id:
        q = q.filter(EmailLog.trader_id == trader_id)
    return q.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit).all()
