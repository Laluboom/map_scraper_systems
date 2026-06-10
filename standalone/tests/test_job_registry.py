import unittest

from job_registry import JobRegistry


class JobRegistryTests(unittest.TestCase):
    def test_successful_job_tracks_lifecycle_and_message(self):
        registry = JobRegistry()

        def task(job):
            registry.update(job.id, "Halfway")

        job = registry.start("scrape", "Dallas, TX", task)

        self.assertTrue(registry.wait(job.id, timeout=2))
        saved = registry.get(job.id)
        self.assertEqual(saved.status, "complete")
        self.assertEqual(saved.message, "Halfway")
        self.assertIsNotNone(saved.started_at)
        self.assertIsNotNone(saved.finished_at)

    def test_failed_job_captures_error(self):
        registry = JobRegistry()

        def task(job):
            raise RuntimeError("boom")

        job = registry.start("send", "Email campaign", task)

        self.assertTrue(registry.wait(job.id, timeout=2))
        saved = registry.get(job.id)
        self.assertEqual(saved.status, "failed")
        self.assertEqual(saved.message, "boom")
        self.assertIn("RuntimeError", saved.error)

    def test_active_and_recent_filter_by_kind(self):
        registry = JobRegistry()

        def task(job):
            registry.update(job.id, "Done")

        scrape = registry.start("scrape", "Scrape", task)
        send = registry.start("send", "Send", task)
        registry.wait(scrape.id, timeout=2)
        registry.wait(send.id, timeout=2)

        self.assertEqual([job.kind for job in registry.recent("scrape")], ["scrape"])
        self.assertEqual([job.kind for job in registry.recent("send")], ["send"])
        self.assertIsNone(registry.active("scrape"))


if __name__ == "__main__":
    unittest.main()
