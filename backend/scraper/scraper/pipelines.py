import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Trader
from app.services.prioritization import extract_product_tags, is_priority


class DeduplicationPipeline:
    def __init__(self):
        self.seen_emails: set[str] = set()

    def process_item(self, item, spider):
        email = (item.get("email") or "").strip().lower()
        if email and email in self.seen_emails:
            from scrapy.exceptions import DropItem
            raise DropItem(f"Duplicate email: {email}")
        if email:
            self.seen_emails.add(email)
        return item


class DatabasePipeline:
    def open_spider(self, spider):
        self.db: Session = SessionLocal()

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        email = (item.get("email") or "").strip().lower()
        if email:
            existing = self.db.query(Trader).filter(Trader.email == email).first()
            if existing:
                return item

        raw_text = item.get("raw_text", "")
        tags = extract_product_tags(raw_text)

        trader = Trader(
            company_name=item.get("company_name"),
            email=email or None,
            phone=item.get("phone"),
            address=item.get("address"),
            city=item.get("city"),
            country=item.get("country"),
            source=item.get("source"),
            product_tags=tags,
            priority_flag=is_priority(tags),
        )
        self.db.add(trader)
        self.db.commit()
        return item
