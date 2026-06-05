import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shed_agent.config import AgentConfig
from shed_agent.extract_listing import extract_listing
from shed_agent.llm_analysis import (
    _get_openai_api_key,
    analyze_observations_with_llm,
    apply_llm_analysis,
    listing_content_hash,
)
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


class LLMAnalysisTests(unittest.TestCase):
    def test_get_openai_api_key_reads_process_environment_first(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-process"}, clear=False):
            self.assertEqual(_get_openai_api_key(), "sk-test-process")

    @patch("shed_agent.llm_analysis.os.name", "nt")
    @patch("shed_agent.llm_analysis.os.getenv", return_value="")
    @patch("shed_agent.llm_analysis.winreg.QueryValueEx", return_value=("sk-test-user", 1))
    @patch("shed_agent.llm_analysis.winreg.OpenKey")
    def test_get_openai_api_key_reads_windows_user_environment(
        self,
        _open_key,
        _query_value_ex,
        _getenv,
    ):
        self.assertEqual(_get_openai_api_key(), "sk-test-user")

    def test_content_hash_changes_with_price(self):
        config = AgentConfig()
        observation = extract_listing("Suncast 4x6 shed - $400")
        first = listing_content_hash(observation, config)
        observation.price = 450
        second = listing_content_hash(observation, config)

        self.assertNotEqual(first, second)

    def test_apply_llm_analysis_updates_business_fields(self):
        observation = score_observation(extract_listing("Garden Igloo Dome - $150. Pickup only."))
        analysis = {
            "product_type": "garden_dome",
            "target_sku_fit": "adjacent_expansion",
            "inferred_size_category": "garden_dome",
            "inferred_brand": "Garden Igloo",
            "condition_assessment": "used_good",
            "delivery_mentioned": False,
            "pickup_required": True,
            "assembly_gap_signal": True,
            "permit_or_placement_relevance": True,
            "business_relevance_score": 5,
            "delivery_assembly_opportunity_score": 8,
            "inventory_learning_value_score": 7,
            "recommended_action": "supplier_research_later",
            "rationale": "Adjacent backyard structure with pickup and assembly friction.",
            "notes_for_weekly_report": "Watch garden dome interest separately.",
        }

        apply_llm_analysis(observation, analysis, "abc", "llm")

        self.assertEqual(observation.analysis_quality, "llm")
        self.assertEqual(observation.product_type, "garden_dome")
        self.assertEqual(observation.target_sku_fit, "adjacent_expansion")
        self.assertTrue(observation.pickup_required)
        self.assertEqual(observation.delivery_assembly_gap_score, 8)

    def test_apply_llm_analysis_normalizes_blank_brand_and_size(self):
        observation = score_observation(extract_listing("Outdoor storage shed - $250 - Bedford, MA"))
        analysis = {
            "product_type": "horizontal_shed",
            "target_sku_fit": "4x6_horizontal",
            "inferred_size_category": "",
            "inferred_brand": "",
            "condition_assessment": "used_good",
            "delivery_mentioned": False,
            "pickup_required": True,
            "assembly_gap_signal": False,
            "permit_or_placement_relevance": False,
            "business_relevance_score": 5,
            "delivery_assembly_opportunity_score": 3,
            "inventory_learning_value_score": 4,
            "recommended_action": "watch",
            "rationale": "Keep existing fallback labels when LLM leaves them blank.",
            "notes_for_weekly_report": "",
        }

        apply_llm_analysis(observation, analysis, "xyz", "llm")

        self.assertEqual(observation.inferred_brand, "unknown")
        self.assertEqual(observation.inferred_size_category, "unknown")

    def test_analyze_observations_falls_back_without_api_key(self):
        config = AgentConfig(enable_llm_analysis=True, max_llm_listings_per_run=1, cache_llm_results=False)
        with patch("shed_agent.llm_analysis._get_openai_api_key", return_value=""):
            with tempfile.TemporaryDirectory() as temp_dir:
                data_path = Path(temp_dir) / "observations.json"
                save_observations([score_observation(extract_listing("Keter 6x5 vertical shed - $500"))], data_path)

                summary = analyze_observations_with_llm(data_path, config)
                saved = load_observations(data_path)

                self.assertEqual(summary.fallback, 1)
                self.assertEqual(summary.errors, ["OPENAI_API_KEY is not set"])
                self.assertEqual(saved[0].analysis_quality, "fallback_only")

    def test_unchanged_fallback_observation_is_not_reanalyzed_without_api_key(self):
        config = AgentConfig(
            enable_llm_analysis=True,
            reanalyze_changed_listings_only=True,
            cache_llm_results=False,
        )
        with patch("shed_agent.llm_analysis._get_openai_api_key", return_value=""):
            with tempfile.TemporaryDirectory() as temp_dir:
                data_path = Path(temp_dir) / "observations.json"
                save_observations([score_observation(extract_listing("Keter 6x5 vertical shed - $500"))], data_path)

                first = analyze_observations_with_llm(data_path, config)
                second = analyze_observations_with_llm(data_path, config)

                self.assertEqual(first.fallback, 1)
                self.assertEqual(second.fallback, 0)
                self.assertEqual(second.skipped_unchanged, 1)
                self.assertEqual(second.errors, ["OPENAI_API_KEY is not set"])
