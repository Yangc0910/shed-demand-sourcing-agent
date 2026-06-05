import unittest

from shed_agent.extract_listing import extract_listing


class LocalSourceTests(unittest.TestCase):
    def test_nextdoor_snippet_is_local_demand_source(self):
        observation = extract_listing(
            "Nextdoor: Looking for a small resin shed near Lexington. Prefer delivery, 4x6 or 6x5.",
            source="nextdoor",
            source_type="nextdoor_snippet",
            location="Lexington MA",
        )

        self.assertTrue(observation.is_local_demand_source)
        self.assertFalse(observation.is_retail_comparable)
        self.assertIn(observation.target_sku_fit, {"4x6_horizontal", "6x5_vertical", "adjacent_expansion"})

    def test_manual_local_post_is_local_demand_source(self):
        observation = extract_listing(
            "Local FB group post: anyone selling a Keter vertical 6 x 5 plastic shed? Need backyard storage.",
            source="local_facebook_group",
            source_type="manual_local_post",
        )

        self.assertTrue(observation.is_local_demand_source)
        self.assertEqual(observation.target_sku_fit, "6x5_vertical")


if __name__ == "__main__":
    unittest.main()
