import unittest
from unittest.mock import patch

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.llm_extract import apply_extracted_fields, extract_supplier_reply
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessage, SupplierThread
from shed_agent.supplier.scoring import score_supplier_candidate


class SupplierLlmScoringTests(unittest.TestCase):
    @patch("shed_agent.supplier.llm_extract._get_openai_api_key", return_value="")
    def test_llm_extraction_falls_back_without_api_key(self, _api_key):
        product = ProductCandidate(supplier_id="supplier-1", product_name="4x6 Shed", product_type="4x6_horizontal")
        message = SupplierMessage(
            thread_id="thread-1",
            direction="inbound",
            message_text="MOQ: 10, USD 210, carton size: 190 x 80 x 35 cm, gross weight: 95 kg, 2 cartons per unit, HDPE.",
        )

        extraction = extract_supplier_reply(message, [product], SupplierConfig(cache_llm_results=False))
        apply_extracted_fields(product, extraction.extracted_fields)

        self.assertEqual(extraction.analysis_quality, "fallback_only")
        self.assertEqual(product.moq, 10)
        self.assertEqual(product.unit_price, 210)
        self.assertEqual(product.material, "HDPE")

    @patch("shed_agent.supplier.llm_extract._get_openai_api_key", return_value="sk-test")
    @patch("shed_agent.supplier.llm_extract.call_openai_structured_json")
    def test_llm_extraction_is_supplemented_by_deterministic_supplier_facts(self, call_openai, _api_key):
        call_openai.return_value = {
            "product_id": "",
            "extracted_fields": {},
            "supplier_extracted_fields": {
                "us_export_experience": "unknown",
                "export_experience_notes": None,
            },
            "missing_information": [],
            "follow_up_questions": [],
            "risk_notes": [],
            "conversation_summary": "Supplier provided a quote.",
            "recommended_next_action": "review quote",
        }
        supplier = Supplier(supplier_name="Experienced Supplier")
        product = ProductCandidate(supplier_id=supplier.supplier_id, product_name="4x6 Shed", product_type="4x6_horizontal")
        message = SupplierMessage(
            thread_id="thread-1",
            direction="inbound",
            message_text="We have exported resin sheds to the United States for five years.",
        )

        extraction = extract_supplier_reply(
            message,
            [product],
            SupplierConfig(cache_llm_results=False),
            supplier,
        )

        self.assertEqual(extraction.analysis_quality, "llm")
        self.assertEqual(extraction.supplier_extracted_fields["us_export_experience"], "yes")

    def test_scoring_distinguishes_strong_and_incomplete_candidates(self):
        supplier = Supplier(supplier_name="Experienced Supplier", us_export_experience="yes")
        strong = ProductCandidate(
            supplier_id=supplier.supplier_id,
            product_name="Strong Shed",
            product_type="4x6_horizontal",
            external_dimensions="72 x 48 x 48 in",
            material="HDPE",
            has_floor="yes",
            uv_weather_resistant="yes",
            unit_price=180,
            moq=8,
            sample_cost=300,
            sample_lead_time="7 days",
            production_lead_time="25 days",
            carton_size="190 x 80 x 35 cm",
            gross_weight=95,
            cartons_per_unit=2,
            estimated_shipping_cost=1200,
            shipping_terms="FOB Ningbo",
            packaging_notes="Reinforced carton",
            english_manual_available="yes",
            installation_video_available="yes",
            spare_parts_available="yes",
            neutral_branding_available="yes",
            warranty_or_after_sales_notes="One year support",
            assembly_notes="Simple two person homeowner assembly",
        )
        incomplete = ProductCandidate(
            supplier_id=supplier.supplier_id,
            product_name="Unknown Shed",
            product_type="other",
        )
        thread = SupplierThread(supplier_id=supplier.supplier_id)

        strong_score = score_supplier_candidate(supplier, strong, thread)
        incomplete_score = score_supplier_candidate(supplier, incomplete, thread)

        self.assertGreater(strong_score.score, incomplete_score.score)
        self.assertEqual(strong_score.recommendation, "strong candidate")
        self.assertIn(incomplete_score.recommendation, {"needs more info", "reject"})
