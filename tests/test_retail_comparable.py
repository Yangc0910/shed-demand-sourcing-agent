import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shed_agent.config import AgentConfig
from shed_agent.generate_daily_digest import generate_daily_digest
from shed_agent.generate_market_report import generate_market_report
from shed_agent.retail_comparable import (
    add_retail_comparable_from_text,
    ingest_retail_comparable_urls,
    is_blocked_or_robot_check,
)


AMAZON_TEXT = """Suncast 4 ft. x 6 ft. Horizontal Resin Outdoor Storage Shed
$529.00
4.4 out of 5 stars
812 reviews
Delivery available
Limited warranty"""

WALMART_TEXT = """Keter 6 x 5 Vertical Resin Outdoor Storage Shed
$679.00
4.2 out of 5 stars
326 reviews
Free delivery
Assembly service available"""

HOME_DEPOT_TEXT = """Rubbermaid Patio Storage Deck Box
$159.00
4.6 out of 5 stars
1,204 reviews
Scheduled delivery available
90 day return policy"""


class RetailComparableTests(unittest.TestCase):
    def test_adds_amazon_4x6_horizontal_retail_comparable(self):
        observation = add_retail_comparable_from_text(
            AMAZON_TEXT,
            url="https://www.amazon.com/example",
            retailer="Amazon",
        )

        self.assertEqual(observation.source_type, "amazon_retail")
        self.assertEqual(observation.target_sku_fit, "4x6_horizontal")
        self.assertEqual(observation.product_type, "horizontal_shed")
        self.assertEqual(observation.price, 529)
        self.assertEqual(observation.rating, 4.4)
        self.assertEqual(observation.review_count, 812)
        self.assertTrue(observation.delivery_available)
        self.assertFalse(observation.is_useful_comparable)

    def test_adds_walmart_6x5_vertical_retail_comparable(self):
        observation = add_retail_comparable_from_text(
            WALMART_TEXT,
            url="https://www.walmart.com/ip/example",
            retailer="Walmart",
        )

        self.assertEqual(observation.source_type, "walmart_retail")
        self.assertEqual(observation.target_sku_fit, "6x5_vertical")
        self.assertEqual(observation.product_type, "vertical_shed")
        self.assertTrue(observation.assembly_service_available)

    def test_adds_home_depot_deck_box_as_adjacent(self):
        observation = add_retail_comparable_from_text(
            HOME_DEPOT_TEXT,
            url="https://www.homedepot.com/p/example",
            retailer="Home Depot",
        )

        self.assertEqual(observation.source_type, "homedepot_retail")
        self.assertEqual(observation.product_type, "deck_box")
        self.assertEqual(observation.target_sku_fit, "adjacent_expansion")
        self.assertEqual(observation.review_count, 1204)

    def test_detects_robot_check_text(self):
        self.assertTrue(is_blocked_or_robot_check("Robot Check: Enter the characters you see below"))

    def test_records_blocked_retail_page_without_retrying(self):
        config = AgentConfig(retail_comparable_urls=["https://www.amazon.com/blocked"])
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "observations.json"
            with patch("shed_agent.retail_comparable.safe_fetch_retail_url", return_value=("Robot Check", "blocked")):
                result = ingest_retail_comparable_urls(config, data_path)

        self.assertEqual(result.blocked, 1)
        self.assertEqual(result.added, 0)

    def test_reports_include_retail_benchmark_section(self):
        config = AgentConfig()
        observations = [
            add_retail_comparable_from_text(AMAZON_TEXT, url="https://www.amazon.com/example", retailer="Amazon"),
            add_retail_comparable_from_text(WALMART_TEXT, url="https://www.walmart.com/ip/example", retailer="Walmart"),
        ]

        daily = generate_daily_digest(observations, config)
        weekly = generate_market_report(observations, config)

        self.assertIn("## Retail Benchmark", daily)
        self.assertIn("## Retail Benchmark", weekly)
        self.assertIn("Amazon", weekly)
        self.assertIn("6x5_vertical", weekly)

    def test_retail_only_data_does_not_create_local_demand_signal(self):
        observations = [
            add_retail_comparable_from_text(AMAZON_TEXT, url="https://www.amazon.com/example", retailer="Amazon"),
            add_retail_comparable_from_text(WALMART_TEXT, url="https://www.walmart.com/ip/example", retailer="Walmart"),
        ]

        weekly = generate_market_report(observations, AgentConfig())
        daily = generate_daily_digest(observations, AgentConfig())

        self.assertIn("Local demand observations reviewed: 0", weekly)
        self.assertIn("Useful local demand comparables: 0", weekly)
        self.assertIn("No priced local comparable observations yet.", weekly)
        self.assertIn("0 local marketplace observations in the last 30 days", weekly)
        self.assertIn("No new high-signal local listings today.", daily)


if __name__ == "__main__":
    unittest.main()
