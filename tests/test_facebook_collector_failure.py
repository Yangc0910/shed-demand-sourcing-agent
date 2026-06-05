import unittest
from pathlib import Path
from unittest.mock import patch

from shed_agent.config import AgentConfig
from shed_agent.facebook_marketplace import collect_facebook_marketplace


class FakeChromium:
    def launch_persistent_context(self, **kwargs):
        raise RuntimeError("headed browser unavailable")


class FakePlaywright:
    chromium = FakeChromium()


class FakePlaywrightManager:
    def __enter__(self):
        return FakePlaywright()

    def __exit__(self, exc_type, exc, tb):
        return False


class FacebookCollectorFailureTests(unittest.TestCase):
    def test_launch_failure_returns_diagnostic_summary(self):
        config = AgentConfig(
            enable_facebook_marketplace_collector=True,
            facebook_search_keywords=["resin shed"],
            headless=False,
        )
        with patch("playwright.sync_api.sync_playwright", return_value=FakePlaywrightManager()):
            summary = collect_facebook_marketplace(config, Path("data/nonexistent-test-observations.json"))

        self.assertEqual(summary.listings_found, 0)
        self.assertTrue(any("browser launch failed" in item.lower() for item in summary.diagnostics))
