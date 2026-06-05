import unittest

from shed_agent.extract_listing import extract_listing
from shed_agent.score_observation import score_observation


class ScoreObservationTests(unittest.TestCase):
    def test_scores_direct_target_as_high_demand(self):
        observation = score_observation(extract_listing("Suncast 4x6 horizontal shed - $425"))

        self.assertEqual(observation.demand_relevance_score, 9)
        self.assertGreaterEqual(observation.price_attractiveness_score, 6)

    def test_delivery_gap_increases_for_pickup_only(self):
        observation = score_observation(extract_listing("6x5 vertical shed $500. Pickup only, assembly required."))

        self.assertGreaterEqual(observation.delivery_assembly_gap_score, 7)
        self.assertGreaterEqual(observation.overall_signal_score, 6)
