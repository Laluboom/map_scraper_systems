from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trader, EmailStatus
from app.schemas import TraderOut

router = APIRouter()


@router.get("/", response_model=List[TraderOut])
def list_traders(
    priority_only: bool = False,
    country: Optional[str] = None,
    source: Optional[str] = None,
    approved: Optional[bool] = None,
    email_status: Optional[EmailStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Trader)
    if priority_only:
        q = q.filter(Trader.priority_flag == True)
    if country:
        q = q.filter(Trader.country.ilike(f"%{country}%"))
    if source:
        q = q.filter(Trader.source == source)
    if approved is not None:
        q = q.filter(Trader.approved == approved)
    if email_status:
        q = q.filter(Trader.email_status == email_status)
    return q.offset(skip).limit(limit).all()


@router.patch("/{trader_id}/approve", response_model=TraderOut)
def approve_trader(trader_id: UUID, db: Session = Depends(get_db)):
    trader = db.query(Trader).filter(Trader.id == trader_id).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader.approved = True
    db.commit()
    db.refresh(trader)
    return trader


@router.patch("/{trader_id}/reject", response_model=TraderOut)
def reject_trader(trader_id: UUID, db: Session = Depends(get_db)):
    trader = db.query(Trader).filter(Trader.id == trader_id).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    trader.approved = False
    db.commit()
    db.refresh(trader)
    return trader
