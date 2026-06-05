import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from shed_agent.facebook_marketplace import (
    FacebookCard,
    _facebook_cdp_endpoint,
    _find_chrome_executable,
    build_marketplace_search_url,
    card_to_observation,
    diagnose_facebook_collector,
    extract_card_from_text,
    extract_detail_metadata,
    expand_user_data_dir,
    format_collection_summary,
    import_facebook_capture_file,
    login_or_challenge_detected,
    normalize_facebook_listing_url,
)
from shed_agent.facebook_marketplace import FacebookCollectionSummary
from shed_agent.config import AgentConfig
from shed_agent.score_observation import score_observation


class FacebookMarketplaceTests(unittest.TestCase):
    def test_builds_keyword_search_url(self):
        url = build_marketplace_search_url("resin shed")

        self.assertEqual(url, "https://www.facebook.com/marketplace/search/?query=resin+shed")

    def test_builds_location_keyword_search_url(self):
        url = build_marketplace_search_url("resin shed", "boston")

        self.assertEqual(url, "https://www.facebook.com/marketplace/boston/search/?query=resin+shed")

    def test_expands_user_data_dir_environment_variable(self):
        path = expand_user_data_dir("%LOCALAPPDATA%/ShedDemandListener/facebook-profile")

        self.assertTrue(str(path))
        self.assertNotIn("%LOCALAPPDATA%", str(path))

    def test_normalizes_listing_url(self):
        url = normalize_facebook_listing_url("/marketplace/item/123456789/?ref=search&foo=bar")

        self.assertEqual(url, "https://www.facebook.com/marketplace/item/123456789")

    def test_extracts_card_from_visible_text(self):
        raw_text = "Suncast 4x6 horizontal shed\n$399\nLexington, MA\nPickup only"
        card = extract_card_from_text(raw_text, "/marketplace/item/123", "Suncast shed")

        self.assertEqual(card.price, 399)
        self.assertEqual(card.location, "Lexington, MA")
        self.assertEqual(card.search_keyword, "Suncast shed")

    def test_extracts_card_title_ignores_marketplace_noise(self):
        raw_text = "Listed today\n$450\nKeter 6x5 resin shed\nWaltham, MA\nPickup only"
        card = extract_card_from_text(raw_text, "/marketplace/item/789", "resin shed")

        self.assertEqual(card.title, "Keter 6x5 resin shed")
        self.assertEqual(card.price, 450)
        self.assertEqual(card.location, "Waltham, MA")

    def test_extracts_card_title_ignores_just_listed_and_free_badges(self):
        raw_text = "Just listed\nFree\nFree Mulch\nWest Newton, MA"
        card = extract_card_from_text(raw_text, "/marketplace/item/790", "Keter shed")

        self.assertEqual(card.title, "Free Mulch")

    def test_extracts_location_embedded_in_facebook_label(self):
        raw_text = "Vista resin shed, $1,000, Marlborough, MA, listing 975569371746018"
        card = extract_card_from_text(raw_text, "/marketplace/item/975569371746018", "resin shed")

        self.assertEqual(card.location, "Marlborough, MA")

    def test_extracts_detail_metadata(self):
        raw_text = """Suncast resin shed
$450
Waltham, MA
Condition: Used
Listed 2 days ago
Buyer must disassemble and pick up."""
        metadata = extract_detail_metadata(raw_text, ["https://example.com/image.jpg"])

        self.assertEqual(metadata["price"], 450)
        self.assertEqual(metadata["location"], "Waltham, MA")
        self.assertEqual(metadata["condition"], "used")
        self.assertEqual(metadata["posted_time"], "Listed 2 days ago")
        self.assertEqual(metadata["image_urls"], ["https://example.com/image.jpg"])
        self.assertTrue(metadata["missing_parts_or_damage_risk"] is False)

    def test_maps_card_to_scored_observation(self):
        card = FacebookCard(
            title="Keter 6x5 vertical shed",
            price=500,
            location="Arlington, MA",
            url="/marketplace/item/456",
            raw_text="Keter 6x5 vertical shed\n$500\nArlington, MA\nPickup only, assembly required",
            search_keyword="Keter shed",
        )
        observation = score_observation(card_to_observation(card))

        self.assertEqual(observation.source_type, "facebook_marketplace_playwright")
        self.assertEqual(observation.target_sku_fit, "6x5_vertical")
        self.assertTrue(observation.pickup_required)
        self.assertGreaterEqual(observation.overall_signal_score, 6)

    def test_card_to_observation_uses_product_title_instead_of_just_listed_badge(self):
        card = FacebookCard(
            title="Just listed",
            price=850,
            location="Westborough, MA",
            url="/marketplace/item/4567",
            raw_text="Just listed\n$850\n9.5'x6' Shed, wood\nWestborough, MA",
            search_keyword="Keter shed",
        )

        observation = card_to_observation(card)

        self.assertEqual(observation.title, "9.5'x6' Shed, wood")
        self.assertEqual(observation.location, "Westborough, MA")

    def test_formats_summary(self):
        summary = FacebookCollectionSummary(
            keywords_searched=["resin shed"],
            listings_found=1,
            new_observations=1,
            duplicates_skipped=0,
            detail_pages_opened=1,
            decision="continue watching",
            decision_reasons=["Need more observations."],
        )

        output = format_collection_summary(summary)

        self.assertIn("Facebook Marketplace Collection Summary", output)
        self.assertIn("Keywords searched: 1", output)
        self.assertIn("Decision:", output)

    def test_formats_summary_diagnostics(self):
        summary = FacebookCollectionSummary(diagnostics=["No listing cards found for keyword 'resin shed'."])

        output = format_collection_summary(summary)

        self.assertIn("Diagnostics:", output)
        self.assertIn("No listing cards found", output)

    def test_detects_two_step_verification_challenge_url(self):
        self.assertTrue(login_or_challenge_detected("https://www.facebook.com/two_step_verification/authentication/", ""))

    def test_builds_cdp_endpoint_from_config_url(self):
        config = AgentConfig(facebook_cdp_url="http://127.0.0.1:9333/")

        self.assertEqual(_facebook_cdp_endpoint(config), "http://127.0.0.1:9333")

    def test_find_chrome_executable_returns_none_for_missing_configured_path(self):
        with patch("shed_agent.facebook_marketplace.shutil.which", return_value=None), patch.dict(
            "os.environ", {"ProgramFiles": "", "ProgramFiles(x86)": "", "LOCALAPPDATA": ""}
        ):
            self.assertIsNone(_find_chrome_executable("C:/definitely/not/a/chrome.exe"))

    def test_diagnose_reports_unreachable_cdp_endpoint(self):
        config = AgentConfig(
            enable_facebook_marketplace_collector=True,
            facebook_launch_mode="cdp",
            facebook_cdp_url="http://127.0.0.1:9444",
            facebook_cdp_port=9444,
        )
        with patch("shed_agent.facebook_marketplace._cdp_endpoint_available", return_value=False), patch(
            "shed_agent.facebook_marketplace._find_chrome_executable", return_value=None
        ):
            diagnostic = diagnose_facebook_collector(config)

        self.assertEqual(diagnostic.status, "blocked")
        self.assertTrue(any("CDP endpoint is not reachable" in item for item in diagnostic.recommendations))

    def test_imports_chrome_extension_capture_file(self):
        payload = {
            "url": "https://www.facebook.com/marketplace/boston/search/?query=resin%20shed",
            "captured_at": "2026-06-02T00:00:00.000Z",
            "cards": [
                {
                    "title": "Keter 6x5 vertical resin shed",
                    "price": "$500",
                    "location": "Waltham, MA",
                    "url": "https://www.facebook.com/marketplace/item/123",
                    "raw_text": "Keter 6x5 vertical resin shed\n$500\nWaltham, MA\nPickup only",
                    "search_keyword": "resin shed",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            capture_path = Path(tmpdir) / "capture.json"
            data_path = Path(tmpdir) / "observations.json"
            capture_path.write_text(json.dumps(payload), encoding="utf-8")

            summary = import_facebook_capture_file(capture_path, data_path, AgentConfig())

        self.assertEqual(summary.listings_found, 1)
        self.assertEqual(summary.new_observations, 1)
        self.assertEqual(summary.high_signal_listings[0].source_type, "facebook_marketplace_playwright")
        self.assertTrue(summary.high_signal_listings[0].is_local_demand_source)
