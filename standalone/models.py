"""SQLite-compatible models (no PostgreSQL-specific types)."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer
from db import Base


class Trader(Base):
    __tablename__ = "traders"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name    = Column(Text)
    email           = Column(Text, index=True)
    phone           = Column(Text)
    address         = Column(Text)
    city            = Column(Text)
    country         = Column(Text)
    source          = Column(Text)
    product_tags    = Column(JSON, default=list)
    priority_flag   = Column(Boolean, default=False)
    priority_score  = Column(Integer, default=0)          # 0-100 from keyword_classifier
    email_valid     = Column(Boolean, nullable=True)
    email_status    = Column(String(20), default="pending")  # pending/sent/bounced/replied
    approved        = Column(Boolean, default=False)
    scraped_at      = Column(DateTime, default=datetime.utcnow)
    sent_at         = Column(DateTime, nullable=True)
    # Google Places fields
    google_place_id = Column(Text, unique=True, nullable=True, index=True)
    google_rating   = Column(Text, nullable=True)
    google_url      = Column(Text, nullable=True)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trader_id     = Column(String(36))
    status        = Column(String(20), default="pending")
    message_id    = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


class ScrapedArea(Base):
    __tablename__ = "scraped_areas"

    id           = Column(Text, primary_key=True)   # "{city}|{state}|{term}"
    scraped_at   = Column(DateTime, default=datetime.utcnow)
    result_count = Column(Integer, default=0)
