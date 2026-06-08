"""Runs Scrapy spiders synchronously and writes results straight to SQLite."""
import re
import configparser
from pathlib import Path
from datetime import datetime

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response

from db import SessionLocal
from models import Trader
from prioritizer import extract_tags, is_priority

_cfg = configparser.ConfigParser()
_cfg.read(Path(__file__).parent / "config.ini")
_proxy = _cfg.get("proxy", "proxy_url", fallback="")

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)\.]{7,}\d")


def _save(item: dict):
    db = SessionLocal()
    try:
        email = (item.get("email") or "").strip().lower()
        if email and db.query(Trader).filter(Trader.email == email).first():
            return
        tags = extract_tags(item.get("raw_text", ""))
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
            scraped_at=datetime.utcnow(),
        )
        db.add(trader)
        db.commit()
    finally:
        db.close()


class _BaseSpider(scrapy.Spider):
    source_name = "unknown"

    def _emails(self, text):
        return EMAIL_RE.findall(text)

    def _phones(self, text):
        return PHONE_RE.findall(text)

    def _item(self, company="", email="", phone="", address="", city="", country="", raw=""):
        phone_clean = re.sub(r"[^\d\+]", "", phone)
        item = {
            "company_name": company.strip(),
            "email": email.strip().lower(),
            "phone": phone_clean,
            "address": address.strip(),
            "city": city.strip(),
            "country": country.strip(),
            "source": self.source_name,
            "raw_text": raw,
        }
        _save(item)
        return item


# --- Each spider class below ---
# PH-009 to PH-018: Fill in the PLACEHOLDER selectors after inspecting each site.

class ISRISpider(_BaseSpider):
    name = "isri"
    source_name = "ISRI"
    start_urls = ["https://www.isri.org/members"]
    LISTING = "PLACEHOLDER_SELECTOR"   # PH-009
    NAME = "PLACEHOLDER_SELECTOR"
    NEXT = "PLACEHOLDER_SELECTOR"

    def parse(self, response: Response):
        for card in response.css(self.LISTING):
            raw = " ".join(card.css("*::text").getall())
            emails = self._emails(raw)
            phones = self._phones(raw)
            yield self._item(card.css(self.NAME).get(""), emails[0] if emails else "", phones[0] if phones else "", raw=raw)
        nxt = response.css(self.NEXT).get()
        if nxt:
            yield response.follow(nxt, self.parse)


class BIRSpider(_BaseSpider):
    name = "bir"
    source_name = "BIR"
    start_urls = ["https://www.bir.org/members"]
    LISTING = "PLACEHOLDER_SELECTOR"   # PH-010
    NAME = "PLACEHOLDER_SELECTOR"
    NEXT = "PLACEHOLDER_SELECTOR"

    def parse(self, response: Response):
        for card in response.css(self.LISTING):
            raw = " ".join(card.css("*::text").getall())
            emails = self._emails(raw)
            phones = self._phones(raw)
            yield self._item(card.css(self.NAME).get(""), emails[0] if emails else "", phones[0] if phones else "", raw=raw)
        nxt = response.css(self.NEXT).get()
        if nxt:
            yield response.follow(nxt, self.parse)


class CARISpider(_BaseSpider):
    name = "cari"
    source_name = "CARI"
    start_urls = ["https://www.cari-acir.org/members"]
    LISTING = "PLACEHOLDER_SELECTOR"   # PH-011
    NAME = "PLACEHOLDER_SELECTOR"
    NEXT = "PLACEHOLDER_SELECTOR"

    def parse(self, response: Response):
        for card in response.css(self.LISTING):
            raw = " ".join(card.css("*::text").getall())
            emails = self._emails(raw)
            phones = self._phones(raw)
            yield self._item(card.css(self.NAME).get(""), emails[0] if emails else "", phones[0] if phones else "", country="Canada", raw=raw)
        nxt = response.css(self.NEXT).get()
        if nxt:
            yield response.follow(nxt, self.parse)


class YellowPagesSpider(_BaseSpider):
    name = "yellowpages"
    source_name = "YellowPages"
    start_urls = ["https://www.yellowpages.com/search?search_terms=scrap+recycling&geo_location_terms=United+States"]
    LISTING = "PLACEHOLDER_SELECTOR"   # PH-012
    NAME = "PLACEHOLDER_SELECTOR"
    DETAIL = "PLACEHOLDER_SELECTOR"
    NEXT = "PLACEHOLDER_SELECTOR"

    def parse(self, response: Response):
        for listing in response.css(self.LISTING):
            url = listing.css(self.DETAIL).get()
            if url:
                yield response.follow(url, self.parse_detail)
        nxt = response.css(self.NEXT).get()
        if nxt:
            yield response.follow(nxt, self.parse)

    def parse_detail(self, response: Response):
        raw = " ".join(response.css("body *::text").getall())
        emails = self._emails(raw)
        phones = self._phones(raw)
        yield self._item(response.css(self.NAME).get(""), emails[0] if emails else "", phones[0] if phones else "", country="US", raw=raw)


class ScrapMonsterSpider(_BaseSpider):
    name = "scrapmonster"
    source_name = "ScrapMonster"
    start_urls = ["https://www.scrapmonster.com/scrap-companies/country/1"]
    LISTING = "PLACEHOLDER_SELECTOR"   # PH-016
    NAME = "PLACEHOLDER_SELECTOR"
    NEXT = "PLACEHOLDER_SELECTOR"

    def parse(self, response: Response):
        for card in response.css(self.LISTING):
            raw = " ".join(card.css("*::text").getall())
            emails = self._emails(raw)
            phones = self._phones(raw)
            yield self._item(card.css(self.NAME).get(""), emails[0] if emails else "", phones[0] if phones else "", country="US", raw=raw)
        nxt = response.css(self.NEXT).get()
        if nxt:
            yield response.follow(nxt, self.parse)


SPIDER_MAP = {
    "isri": ISRISpider,
    "bir": BIRSpider,
    "cari": CARISpider,
    "yellowpages": YellowPagesSpider,
    "scrapmonster": ScrapMonsterSpider,
}


def run_spider(source: str):
    spider_cls = SPIDER_MAP.get(source)
    if not spider_cls:
        raise ValueError(f"Unknown source '{source}'. Valid: {list(SPIDER_MAP)}")

    settings = {
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "LOG_LEVEL": "WARNING",
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if _proxy:
        settings["DOWNLOADER_MIDDLEWARES"] = {"scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 750}

    process = CrawlerProcess(settings)
    process.crawl(spider_cls)
    process.start()
