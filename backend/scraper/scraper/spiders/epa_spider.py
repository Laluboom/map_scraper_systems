from scrapy.http import Response
from .base_spider import BaseTraderSpider


class EPASpider(BaseTraderSpider):
    """
    Scrapes EPA certified trader / facility lists.

    PH-018: The EPA publishes various facility data at https://www.epa.gov/enviro.
    - Find the correct export/search URL for certified scrap/recycling facilities.
    - Update start_urls and all PLACEHOLDER selectors below.
    - EPA data may be available as CSV/Excel exports — if so, implement parse() to
      read the downloaded file instead of HTML scraping.
    """

    name = "epa"
    source_name = "EPA"

    # PLACEHOLDER — find the correct EPA data export URL (PH-018)
    start_urls = ["https://www.epa.gov/PLACEHOLDER_EPA_FACILITY_SEARCH_URL"]
    LISTING_SEL = "PLACEHOLDER_LISTING_SELECTOR"
    NAME_SEL = "PLACEHOLDER_NAME_SELECTOR"
    PHONE_SEL = "PLACEHOLDER_PHONE_SELECTOR"
    CITY_SEL = "PLACEHOLDER_CITY_SELECTOR"
    STATE_SEL = "PLACEHOLDER_STATE_SELECTOR"

    def parse(self, response: Response):
        for row in response.css(self.LISTING_SEL):
            raw_text = " ".join(row.css("*::text").getall())
            emails = self.extract_emails(raw_text)
            phones = self.extract_phones(raw_text)
            yield self.make_item(
                company_name=row.css(self.NAME_SEL).get("").strip(),
                email=emails[0] if emails else "",
                phone=phones[0] if phones else "",
                city=row.css(self.CITY_SEL).get("").strip(),
                country="US",
                raw_text=raw_text,
            )
