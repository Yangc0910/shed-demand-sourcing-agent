import unittest

from shed_agent.extract_listing import extract_listing, refresh_extraction


class ExtractListingTests(unittest.TestCase):
    def test_extracts_direct_vertical_listing(self):
        observation = extract_listing("Keter 6 x 5 vertical outdoor shed - $620\nCan deliver locally.")

        self.assertEqual(observation.price, 620)
        self.assertEqual(observation.size_raw, "6x5")
        self.assertEqual(observation.product_type, "vertical_shed")
        self.assertEqual(observation.inferred_size_category, "6x5_vertical")
        self.assertEqual(observation.inferred_brand, "Keter")
        self.assertTrue(observation.delivery_mentioned)

    def test_detects_transport_pain_point(self):
        observation = extract_listing("Suncast 4x6 horizontal shed $425. Pickup only, bring truck.")

        self.assertEqual(observation.inferred_size_category, "4x6_horizontal")
        self.assertTrue(observation.pickup_required)

    def test_large_shed_is_not_useful_comparable(self):
        observation = extract_listing("Lifetime plastic storage shed 7x7 - $900")

        self.assertFalse(observation.is_useful_comparable)
        self.assertEqual(observation.target_sku_fit, "not_relevant")

    def test_deck_box_has_explicit_category(self):
        observation = extract_listing("Rubbermaid deck box - $120. Patio cushion storage box.")

        self.assertEqual(observation.product_type, "deck_box")
        self.assertEqual(observation.inferred_size_category, "deck_box")
        self.assertEqual(observation.target_sku_fit, "adjacent_expansion")

    def test_garden_dome_is_adjacent_expansion(self):
        observation = extract_listing("Garden Igloo Dome - $150. Just listed, buyer must pick up and assemble.")

        self.assertEqual(observation.product_type, "garden_dome")
        self.assertEqual(observation.target_sku_fit, "adjacent_expansion")
        self.assertTrue(observation.pickup_required)
        self.assertTrue(observation.assembly_mentioned)

    def test_recognizes_6x5_resin_shed_without_vertical_word(self):
        observation = extract_listing("Keter resin outdoor storage shed 6 ft x 5 ft - $480. Local pickup only.")

        self.assertEqual(observation.product_type, "vertical_shed")
        self.assertEqual(observation.target_sku_fit, "6x5_vertical")
        self.assertTrue(observation.pickup_required)

    def test_recognizes_4x6_low_profile_shed(self):
        observation = extract_listing("Suncast low-profile plastic shed 4 x 6 $320. Can deliver nearby.")

        self.assertEqual(observation.product_type, "horizontal_shed")
        self.assertEqual(observation.target_sku_fit, "4x6_horizontal")
        self.assertTrue(observation.delivery_mentioned)

    def test_detects_missing_parts_and_fast_signal_notes(self):
        observation = extract_listing("Outdoor storage shed $200. Just listed, missing hardware, as is.")

        self.assertIn("Missing parts or damage risk detected.", observation.extraction_notes)
        self.assertIn("Fast-moving or visible-interest signal detected.", observation.extraction_notes)

    def test_extracts_marketplace_price_location_and_dimension_format(self):
        observation = extract_listing(
            "Vista 7 ft. W x 10 ft. D Plastic Resin Storage Shed, $1,000, Marlborough, MA",
            source="facebook",
            source_type="facebook_marketplace_playwright",
        )

        self.assertEqual(observation.price, 1000)
        self.assertEqual(observation.location, "Marlborough, MA")
        self.assertEqual(observation.size_raw, "7x10")
        self.assertEqual(observation.product_type, "large_shed")

    def test_refresh_extraction_updates_location(self):
        observation = extract_listing("Modernist 6 Ft. X 5 Ft. Resin Storage Shed A8062, $89, Brockton, MA")
        observation.location = ""

        refreshed = refresh_extraction(observation)

        self.assertEqual(refreshed.location, "Brockton, MA")
