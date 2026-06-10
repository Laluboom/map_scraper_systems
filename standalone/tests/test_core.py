import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from area_manager import is_done, mark_done
from db import Base
from email_sender import build_email_body
from keyword_classifier import is_priority, score_company
from models import ScrapedArea
from website_email_extractor import extract_email_and_text


class KeywordClassifierTests(unittest.TestCase):
    def test_scores_priority_company_from_name_type_and_website_text(self):
        score, tags = score_company(
            name="Dallas Copper Scrap Recycling",
            google_types=["recycling_center"],
            website_text="We buy electric motors and copper cable.",
        )

        self.assertEqual(score, 100)
        self.assertTrue(is_priority(score, threshold=40))
        self.assertIn("scrap", tags)
        self.assertIn("recycling_center", tags)
        self.assertIn("electric motor", tags)
        self.assertIn("copper cable", tags)

    def test_secondary_type_scores_below_default_priority_threshold(self):
        score, tags = score_company(
            name="General Supply Co",
            google_types=["industrial_supplier"],
            website_text="",
        )

        self.assertEqual(score, 20)
        self.assertFalse(is_priority(score, threshold=40))
        self.assertEqual(tags, ["industrial_supplier"])


class WebsiteEmailExtractorTests(unittest.TestCase):
    def test_extracts_non_generic_email_from_homepage(self):
        with patch(
            "website_email_extractor._fetch",
            return_value="Contact sales@example.com or support@example.com",
        ) as fetch:
            email, text = extract_email_and_text("https://example.com")

        self.assertEqual(email, "sales@example.com")
        self.assertIn("support@example.com", text)
        fetch.assert_called_once_with("https://example.com")

    def test_falls_back_to_contact_page_when_homepage_has_no_email(self):
        pages = {
            "https://example.com": "<html>No email here</html>",
            "https://example.com/contact": "Email owner@example.com",
        }

        with patch("website_email_extractor._fetch", side_effect=lambda url: pages.get(url, "")):
            email, text = extract_email_and_text("https://example.com")

        self.assertEqual(email, "owner@example.com")
        self.assertIn("No email here", text)
        self.assertIn("owner@example.com", text)


class AreaManagerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_mark_done_and_resume_window(self):
        db = self.Session()
        try:
            self.assertFalse(is_done(db, "Dallas", "TX", "scrap yard", rescrape_days=30))

            mark_done(db, "Dallas", "TX", "scrap yard", result_count=4)

            self.assertTrue(is_done(db, "Dallas", "TX", "scrap yard", rescrape_days=30))
            self.assertFalse(is_done(db, "Dallas", "TX", "scrap yard", rescrape_days=0))

            area = db.query(ScrapedArea).first()
            self.assertEqual(area.result_count, 4)
        finally:
            db.close()

    def test_old_area_is_not_done(self):
        db = self.Session()
        try:
            mark_done(db, "Austin", "TX", "copper recycling", result_count=2)
            area = db.query(ScrapedArea).first()
            area.scraped_at = datetime.utcnow() - timedelta(days=31)
            db.commit()

            self.assertFalse(is_done(db, "Austin", "TX", "copper recycling", rescrape_days=30))
        finally:
            db.close()


class EmailTemplateTests(unittest.TestCase):
    def test_build_email_body_fills_placeholders(self):
        body = build_email_body(
            "Gulf Metals LLC",
            "Dear {greeting},\nCompany: {company_name}",
        )

        self.assertEqual(body, "Dear Gulf Metals LLC,\nCompany: Gulf Metals LLC")

    def test_build_email_body_falls_back_when_unknown_placeholder_exists(self):
        body = build_email_body("Gulf Metals LLC", "Dear {unknown},")

        self.assertEqual(body, "Dear {unknown},")


if __name__ == "__main__":
    unittest.main()
