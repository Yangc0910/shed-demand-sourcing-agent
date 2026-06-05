import unittest

from shed_agent.config import AgentConfig
from shed_agent.generate_daily_digest import generate_daily_digest
from shed_agent.generate_market_report import generate_market_report
from shed_agent.models import MarketObservation
from shed_agent.sample_data import build_sample_observations


class GenerateReportTests(unittest.TestCase):
    def test_weekly_report_contains_key_sections(self):
        report = generate_market_report(build_sample_observations(), AgentConfig())

        self.assertIn("Local Shed Market Report", report)
        self.assertIn("Suggested Local Price Targets", report)
        self.assertIn("until at least 3 useful local comparables are observed", report)
        self.assertIn("Inventory Decision Signals", report)
        self.assertIn("Adjacent Backyard Opportunity Watchlist", report)
        self.assertIn("Local Demand Signals", report)
        self.assertIn("Retail Benchmark", report)
        self.assertIn("Delivery/Assembly Gap", report)
        self.assertIn("Buyer is responsible", report)
        self.assertIn("Decision:", report)

    def test_weekly_report_ignores_blank_brand_and_size_buckets(self):
        observation = MarketObservation(
            source="facebook",
            source_type="facebook_marketplace_playwright",
            title="Noise listing",
            description_raw="Noise listing",
            inferred_brand="",
            inferred_size_category="",
        )

        report = generate_market_report([observation], AgentConfig())

        self.assertNotIn("- Local brands: :", report)
        self.assertNotIn("- Local sizes/categories: :", report)

    def test_daily_digest_contains_key_sections(self):
        digest = generate_daily_digest(build_sample_observations(), AgentConfig())

        self.assertIn("Daily Shed Demand Digest", digest)
        self.assertIn("Local Demand Signals", digest)
        self.assertIn("Fast-Moving / Interest Signals", digest)
        self.assertIn("Keter 6 x 5 vertical outdoor shed", digest)
        self.assertIn("Adjacent Backyard Opportunity Watchlist", digest)
        self.assertIn("Inventory Decision Signals", digest)
