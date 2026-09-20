import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import places_scraper
from db import Base
from models import ScrapedArea


class PlacesApiErrorStatusTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_request_denied_status_leaves_area_unmarked_done(self):
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "error_message": "You must enable Billing on the Google Cloud Project.",
            "results": [{"place_id": "should-not-be-used"}],
        }

        with patch("places_scraper.SessionLocal", self.Session), \
             patch("places_scraper.check_text_search"), \
             patch("places_scraper.httpx.get", return_value=fake_response):
            places_scraper.run_places_scrape(
                api_key="fake-key",
                cities=[("Dallas", "TX")],
                search_terms=["scrap yard"],
                print_fn=lambda *a, **k: None,
            )

        db = self.Session()
        try:
            self.assertEqual(db.query(ScrapedArea).count(), 0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
