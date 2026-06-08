from scrapy.http import Response
from .base_spider import BaseTraderSpider


class YellowPagesSpider(BaseTraderSpider):
    """
    Scrapes Yellow Pages for scrap/recycling businesses.

    PH-012: After inspecting https://www.yellowpages.com/search?search_terms=scrap+recycling,
    update all PLACEHOLDER selectors. Pagination is typically ?page=N.
    """

    name = "yellowpages"
    source_name = "YellowPages"

    SEARCH_TERMS = "scrap+recycling"
    # PLACEHOLDER — update regions via spider argument or a list of US city slugs
    start_urls = [
        f"https://www.yellowpages.com/search?search_terms={SEARCH_TERMS}&geo_location_terms=United+States"
    ]

    LISTING_SEL = "PLACEHOLDER_LISTING_SELECTOR"        # PH-012
    NAME_SEL = "PLACEHOLDER_NAME_SELECTOR"
    PHONE_SEL = "PLACEHOLDER_PHONE_SELECTOR"
    ADDRESS_SEL = "PLACEHOLDER_ADDRESS_SELECTOR"
    CITY_SEL = "PLACEHOLDER_CITY_SELECTOR"
    DETAIL_LINK_SEL = "PLACEHOLDER_DETAIL_LINK_SELECTOR"
    NEXT_PAGE_SEL = "PLACEHOLDER_NEXT_PAGE_SELECTOR"

    def __init__(self, regions=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regions = regions or []

    def parse(self, response: Response):
        for listing in response.css(self.LISTING_SEL):
            detail_url = listing.css(self.DETAIL_LINK_SEL).get()
            if detail_url:
                yield response.follow(detail_url, self.parse_detail)

        next_page = response.css(self.NEXT_PAGE_SEL).get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_detail(self, response: Response):
        raw_text = " ".join(response.css("body *::text").getall())
        emails = self.extract_emails(raw_text)
        phones = self.extract_phones(raw_text)
        yield self.make_item(
            company_name=response.css(self.NAME_SEL).get("").strip(),
            email=emails[0] if emails else "",
            phone=phones[0] if phones else "",
            address=response.css(self.ADDRESS_SEL).get("").strip(),
            city=response.css(self.CITY_SEL).get("").strip(),
            country="US",
            raw_text=raw_text,
        )
