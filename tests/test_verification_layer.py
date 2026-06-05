import unittest

from shed_agent.config import AgentConfig
from shed_agent.extract_listing import extract_listing
from shed_agent.llm_analysis import apply_fallback_verification
from shed_agent.score_observation import score_observation
from shed_agent.verification_report import format_candidate_verification_section


class VerificationLayerTests(unittest.TestCase):
    def test_nonlocal_partner_listing_is_likely_noise(self):
        observation = extract_listing(
            "Partner listing Light Grey 6x6 Ft Waterproof Resin Storage Shed, $983, Citrus Heights, CA",
            source="facebook",
            source_type="facebook_marketplace_playwright",
        )

        apply_fallback_verification(observation, AgentConfig())
        scored = score_observation(observation, AgentConfig())

        self.assertEqual(scored.verification_status, "likely_noise")
        self.assertEqual(scored.demand_match, "retail_like_or_partner_listing")
        self.assertLessEqual(scored.demand_relevance_score, 2)

    def test_target_candidate_is_watch_uncertain_not_discarded(self):
        observation = extract_listing(
            "Modernist 6 Ft. X 5 Ft. Resin Storage Shed A8062, $89, Brockton, MA",
            source="facebook",
            source_type="facebook_marketplace_playwright",
        )

        apply_fallback_verification(observation, AgentConfig())
        scored = score_observation(observation, AgentConfig())

        self.assertEqual(scored.target_sku_fit, "6x5_vertical")
        self.assertEqual(scored.verification_status, "watch_uncertain")
        self.assertEqual(scored.demand_match, "target_candidate")
        self.assertGreaterEqual(scored.demand_relevance_score, 8)

    def test_sponsored_ad_text_in_detail_does_not_make_local_listing_partner_noise(self):
        observation = extract_listing(
            "Lifetime plastic shed, $200, Tyngsboro, MA\nSponsored ad text elsewhere on page",
            source="facebook",
            source_type="facebook_marketplace_playwright",
        )

        apply_fallback_verification(observation, AgentConfig())

        self.assertNotEqual(observation.demand_match, "retail_like_or_partner_listing")
        self.assertNotEqual(observation.verification_status, "likely_noise")

    def test_verification_report_surfaces_noise_and_uncertain(self):
        noise = extract_listing("Free white landscaping rocks, $0, Haverhill, MA", "facebook", "facebook_marketplace_playwright")
        target = extract_listing(
            "Modernist 6 Ft. X 5 Ft. Resin Storage Shed A8062, $89, Brockton, MA",
            "facebook",
            "facebook_marketplace_playwright",
        )
        for item in (noise, target):
            apply_fallback_verification(item, AgentConfig())

        lines = "\n".join(format_candidate_verification_section([noise, target]))

        self.assertIn("Candidate Verification / Learning", lines)
        self.assertIn("Likely Noise", lines)
        self.assertIn("Watch-Uncertain", lines)


if __name__ == "__main__":
    unittest.main()
