from __future__ import annotations
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models import EmailStatus


class TraderOut(BaseModel):
    id: UUID
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    source: Optional[str]
    product_tags: List[str]
    priority_flag: bool
    email_valid: Optional[bool]
    email_status: EmailStatus
    approved: bool
    scraped_at: datetime

    class Config:
        from_attributes = True


class TraderFilter(BaseModel):
    priority_only: bool = False
    country: Optional[str] = None
    source: Optional[str] = None
    approved: Optional[bool] = None
    email_status: Optional[EmailStatus] = None


class CampaignCreate(BaseModel):
    name: str
    target_regions: List[str]


class CampaignOut(BaseModel):
    id: UUID
    name: str
    status: str
    total_traders: str
    sent_count: str
    bounced_count: str
    replied_count: str
    created_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class EmailLogOut(BaseModel):
    id: UUID
    trader_id: UUID
    campaign_id: Optional[UUID]
    status: EmailStatus
    sendgrid_message_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ScrapeStartRequest(BaseModel):
    source: str
    regions: Optional[List[str]] = None
