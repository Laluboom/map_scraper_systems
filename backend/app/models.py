import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ARRAY, Enum as SAEnum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class EmailStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    bounced = "bounced"
    replied = "replied"


class Trader(Base):
    __tablename__ = "traders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(Text)
    email = Column(Text, index=True)
    phone = Column(Text)
    address = Column(Text)
    city = Column(Text)
    country = Column(Text)
    source = Column(Text)
    product_tags = Column(ARRAY(Text), default=[])
    priority_flag = Column(Boolean, default=False)
    email_valid = Column(Boolean, nullable=True)
    email_status = Column(SAEnum(EmailStatus), default=EmailStatus.pending)
    approved = Column(Boolean, default=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    logs = relationship("EmailLog", back_populates="trader")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text)
    status = Column(Text, default="created")  # created, running, paused, done
    target_regions = Column(ARRAY(Text), default=[])
    total_traders = Column(Text, default="0")
    sent_count = Column(Text, default="0")
    bounced_count = Column(Text, default="0")
    replied_count = Column(Text, default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    logs = relationship("EmailLog", back_populates="campaign")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), ForeignKey("traders.id"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    status = Column(SAEnum(EmailStatus), default=EmailStatus.pending)
    sendgrid_message_id = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    approved_by = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trader = relationship("Trader", back_populates="logs")
    campaign = relationship("Campaign", back_populates="logs")
