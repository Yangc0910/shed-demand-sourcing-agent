import unittest
from unittest.mock import patch

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.followup import generate_follow_up_plan
from shed_agent.supplier.message_queue import approve_message_draft, build_follow_up_draft, mark_message_sent_manually
from shed_agent.supplier.models import ProductCandidate, SupplierThread
from shed_agent.supplier.rfq import generate_rfq_template


class SupplierRfqFollowUpQueueTests(unittest.TestCase):
    def test_rfq_contains_required_questions_in_both_languages(self):
        templates = generate_rfq_template("4x6_horizontal", SupplierConfig())

        self.assertIn("MOQ", templates["english"])
        self.assertIn("English installation manual", templates["english"])
        self.assertIn("Boston", templates["english"])
        self.assertIn("最小起订量", templates["chinese"])
        self.assertIn("英文安装说明书", templates["chinese"])
        self.assertIn("波士顿", templates["chinese"])

    @patch("shed_agent.supplier.message_queue._get_openai_api_key", return_value="")
    def test_follow_up_generation_and_approval_workflow(self, _api_key):
        product = ProductCandidate(supplier_id="supplier-1", product_name="Incomplete Shed", product_type="4x6_horizontal")
        thread = SupplierThread(supplier_id="supplier-1", product_ids=[product.product_id])

        plan = generate_follow_up_plan(thread, [product])
        draft = build_follow_up_draft(plan, "Example Supplier", SupplierConfig())

        self.assertIn("moq", plan.missing_information)
        self.assertIn("Please confirm the MOQ", draft.draft_text_english)
        self.assertEqual(draft.approval_status, "pending")

        approve_message_draft(draft)
        self.assertEqual(draft.approval_status, "approved")
        mark_message_sent_manually(draft)
        self.assertEqual(draft.approval_status, "sent_manually")
