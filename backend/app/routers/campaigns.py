from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Campaign
from app.schemas import CampaignCreate, CampaignOut
from app.tasks.email_tasks import run_campaign

router = APIRouter()


@router.post("/start", response_model=CampaignOut)
def start_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    campaign = Campaign(
        name=payload.name,
        target_regions=payload.target_regions,
        status="created",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    run_campaign.delay(str(campaign.id))
    return campaign


@router.get("/{campaign_id}/status", response_model=CampaignOut)
def campaign_status(campaign_id: UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()
