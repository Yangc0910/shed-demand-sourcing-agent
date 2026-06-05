import tempfile
import unittest
from pathlib import Path

from shed_agent.config import AgentConfig
from shed_agent.deduplicate import merge_observations
from shed_agent.decision import decision_check
from shed_agent.extract_listing import extract_listing
from shed_agent.ingest import ingest_craigslist_rss, parse_craigslist_rss
from shed_agent.sample_data import MOCK_CRAIGSLIST_RSS, build_sample_observations
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations


class IngestAndDecisionTests(unittest.TestCase):
    def test_merge_refines_badge_title_from_same_listing_url(self):
        current = extract_listing(
            "Just listed\n$850\n9.5'x6' Shed, wood\nWestborough, MA",
            source="facebook",
            source_type="facebook_marketplace_playwright",
            url="https://www.facebook.com/marketplace/item/123",
        )
        current.title = "Just listed"
        incoming = extract_listing(
            "9.5'x6' Shed, wood\n$850\nWestborough, MA",
            source="facebook",
            source_type="facebook_marketplace_playwright",
            url="https://www.facebook.com/marketplace/item/123",
        )

        merged, new_items, changes = merge_observations([current], [incoming])

        self.assertEqual(new_items, [])
        self.assertEqual(merged[0].title, "9.5'x6' Shed, wood")
        self.assertTrue(any("Title refined" in change for change in changes))

    def test_parse_mock_craigslist_rss(self):
        observations = parse_craigslist_rss(MOCK_CRAIGSLIST_RSS, "mock")

        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0].source_type, "craigslist_rss")
        self.assertEqual(observations[0].target_sku_fit, "4x6_horizontal")

    def test_ingest_craigslist_rss_from_file_url(self):
        fixture = Path(__file__).parent / "fixtures" / "mock_craigslist.rss"
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "observations.json"
            count, changes = ingest_craigslist_rss(AgentConfig(), data_path, [f"file://{fixture}"])

            self.assertEqual(count, 2)
            self.assertEqual(len(load_observations(data_path)), 2)
            self.assertTrue(changes)

    def test_decision_check_returns_supported_recommendation(self):
        decision, reasons = decision_check(build_sample_observations(), AgentConfig())

        self.assertIn(decision, {"continue watching", "start supplier RFQ", "inventory candidate", "no-go"})
        self.assertTrue(reasons)

    def test_decision_does_not_no_go_from_noisy_nonlocal_facebook_results(self):
        config = AgentConfig(target_locations=["Lexington", "Burlington", "Waltham", "Arlington"])
        raw_items = [
            "Light Grey 6x6 Ft Waterproof Resin Storage Shed With Lockable Doors, $983, Citrus Heights, CA",
            "Shed Metal Hasp Latch Lock For Rubbermaid Storage Shed, $25, Citrus Heights, CA",
            "Free white landscaping rocks, $0, Haverhill, MA",
            "Green house, $0, Boxford, MA",
            "Arrow Yardsaver 4 x 7 storage shed, $110, Medway, MA",
            "Outdoor storage shed, $200, Bedford, MA",
            "New storage shed, $250, East Weymouth, MA",
        ]
        observations = [
            score_observation(extract_listing(raw, "facebook", "facebook_marketplace_playwright"), config)
            for raw in raw_items
        ]

        decision, reasons = decision_check(observations, config)

        self.assertEqual(decision, "continue watching")
        self.assertTrue(any("explicit non-local results" in reason for reason in reasons))
