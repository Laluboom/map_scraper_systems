import re
import scrapy
from scraper.items import TraderItem


EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)\.]{7,}\d")


class BaseTraderSpider(scrapy.Spider):
    """Shared helpers for all trader spiders."""

    source_name: str = "unknown"

    def extract_emails(self, text: str) -> list[str]:
        return EMAIL_RE.findall(text)

    def extract_phones(self, text: str) -> list[str]:
        return PHONE_RE.findall(text)

    def normalize_phone(self, phone: str) -> str:
        return re.sub(r"[^\d\+]", "", phone)

    def make_item(
        self,
        company_name: str = "",
        email: str = "",
        phone: str = "",
        address: str = "",
        city: str = "",
        country: str = "",
        raw_text: str = "",
    ) -> TraderItem:
        item = TraderItem()
        item["company_name"] = company_name.strip()
        item["email"] = email.strip().lower()
        item["phone"] = self.normalize_phone(phone)
        item["address"] = address.strip()
        item["city"] = city.strip()
        item["country"] = country.strip()
        item["source"] = self.source_name
        item["raw_text"] = raw_text
        return item
