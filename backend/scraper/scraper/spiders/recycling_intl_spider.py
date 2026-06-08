from scrapy.http import Response
from .base_spider import BaseTraderSpider


class RecyclingIntlSpider(BaseTraderSpider):
    """
    Scrapes Recycling International directory.

    PH-017: Inspect https://www.recyclinginternational.com and update all PLACEHOLDER selectors.
    """

    name = "recycling_intl"
    source_name = "RecyclingInternational"

    start_urls = ["https://www.recyclinginternational.com/recycling-news/"]
    LISTING_SEL = "PLACEHOLDER_LISTING_SELECTOR"   # PH-017
    NAME_SEL = "PLACEHOLDER_NAME_SELECTOR"
    PHONE_SEL = "PLACEHOLDER_PHONE_SELECTOR"
    CITY_SEL = "PLACEHOLDER_CITY_SELECTOR"
    COUNTRY_SEL = "PLACEHOLDER_COUNTRY_SELECTOR"
    NEXT_PAGE_SEL = "PLACEHOLDER_NEXT_PAGE_SELECTOR"

    def parse(self, response: Response):
        for card in response.css(self.LISTING_SEL):
            raw_text = " ".join(card.css("*::text").getall())
            emails = self.extract_emails(raw_text)
            phones = self.extract_phones(raw_text)
            yield self.make_item(
                company_name=card.css(self.NAME_SEL).get("").strip(),
                email=emails[0] if emails else "",
                phone=phones[0] if phones else "",
                city=card.css(self.CITY_SEL).get("").strip(),
                country=card.css(self.COUNTRY_SEL).get("").strip(),
                raw_text=raw_text,
            )

        next_page = response.css(self.NEXT_PAGE_SEL).get()
        if next_page:
            yield response.follow(next_page, self.parse)
