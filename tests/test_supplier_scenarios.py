import tempfile
import unittest
from pathlib import Path

from shed_agent.cli import main
from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.conversation import analyze_supplier_thread
from shed_agent.supplier.followup import generate_follow_up_plan
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessage, SupplierThread
from shed_agent.supplier.scoring import score_supplier_candidate
from shed_agent.supplier.storage import load_product_candidates, load_supplier_threads, load_suppliers


FIXTURES = Path(__file__).parent / "fixtures"


class SupplierScenarioTests(unittest.TestCase):
    def test_strong_candidate_fallback_extracts_complete_quote_and_scores_high(self):
        supplier, product, thread = self._analyze_fixture(
            "supplier_scenario_1_strong_reply.txt",
            "Jiangsu Bright Outdoor Products",
            "RS-H46 Horizontal Resin Shed",
            "4x6_horizontal",
        )

        score = score_supplier_candidate(supplier, product, thread)
        plan = generate_follow_up_plan(thread, [product], supplier)

        self.assertEqual(product.moq, 10)
        self.assertEqual(product.price_tiers["10"], 218)
        self.assertEqual(product.carton_size, "190 x 84 x 38 cm")
        self.assertEqual(product.english_manual_available, "yes")
        self.assertEqual(product.installation_video_available, "yes")
        self.assertEqual(product.spare_parts_available, "yes")
        self.assertEqual(supplier.us_export_experience, "yes")
        self.assertEqual(plan.missing_information, [])
        self.assertEqual(score.recommendation, "strong candidate")
        self.assertGreaterEqual(score.score, 8.0)

    def test_incomplete_candidate_generates_focused_missing_information(self):
        supplier, product, thread = self._analyze_fixture(
            "supplier_scenario_2_incomplete_reply.txt",
            "Zhejiang Garden Storage Co",
            "VS-65 Vertical Resin Shed",
            "6x5_vertical",
        )

        plan = generate_follow_up_plan(thread, [product], supplier)
        score = score_supplier_candidate(supplier, product, thread)

        for item in (
            "internal dimensions",
            "price tiers 5/10/20/50",
            "sample",
            "carton size",
            "gross weight",
            "cartons per unit",
            "shipping",
            "installation video",
            "spare parts",
            "us export experience",
        ):
            self.assertIn(item, plan.missing_information)
        self.assertEqual(score.recommendation, "needs more info")

    def test_high_risk_candidate_is_rejected(self):
        supplier, product, thread = self._analyze_fixture(
            "supplier_scenario_3_high_risk_reply.txt",
            "Shandong Low Cost Plastics",
            "PL-SHED-46 Plastic Shed",
            "4x6_horizontal",
        )

        score = score_supplier_candidate(supplier, product, thread)

        self.assertEqual(product.moq, 100)
        self.assertEqual(product.english_manual_available, "no")
        self.assertEqual(product.installation_video_available, "no")
        self.assertEqual(product.spare_parts_available, "no")
        self.assertEqual(supplier.us_export_experience, "no")
        self.assertEqual(score.recommendation, "reject")
        self.assertLess(score.score, 4.0)

    def test_cli_reuses_queued_rfq_thread_for_supplier_reply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            common = [
                "--suppliers-data",
                str(root / "suppliers.json"),
                "--products-data",
                str(root / "products.json"),
                "--threads-data",
                str(root / "threads.json"),
                "--message-queue-data",
                str(root / "queue.json"),
            ]
            self.assertEqual(main(common + ["add-supplier", "--name", "Thread Reuse Supplier", "--platform", "Alibaba"]), 0)
            supplier = load_suppliers(root / "suppliers.json")[0]
            self.assertEqual(
                main(
                    common
                    + [
                        "add-product-candidate",
                        "--supplier-id",
                        supplier.supplier_id,
                        "--name",
                        "Thread Reuse Shed",
                        "--product-type",
                        "4x6_horizontal",
                    ]
                ),
                0,
            )
            product = load_product_candidates(root / "products.json")[0]
            self.assertEqual(
                main(
                    common
                    + [
                        "generate-rfq-template",
                        "--product-type",
                        "4x6_horizontal",
                        "--queue-for-supplier",
                        supplier.supplier_id,
                        "--out",
                        str(root / "rfq.md"),
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    common
                    + [
                        "add-supplier-message",
                        "--supplier-id",
                        supplier.supplier_id,
                        "--product-id",
                        product.product_id,
                        "--direction",
                        "inbound",
                        "--text",
                        "MOQ is 10 sets.",
                    ]
                ),
                0,
            )

            threads = load_supplier_threads(root / "threads.json")
            self.assertEqual(len(threads), 1)
            self.assertEqual(threads[0].product_ids, [product.product_id])
            self.assertEqual(len(threads[0].messages), 1)

    def _analyze_fixture(
        self,
        fixture_name: str,
        supplier_name: str,
        product_name: str,
        product_type: str,
    ) -> tuple[Supplier, ProductCandidate, SupplierThread]:
        supplier = Supplier(supplier_name=supplier_name)
        product = ProductCandidate(
            supplier_id=supplier.supplier_id,
            product_name=product_name,
            product_type=product_type,
        )
        thread = SupplierThread(supplier_id=supplier.supplier_id, product_ids=[product.product_id])
        thread.messages.append(
            SupplierMessage(
                thread_id=thread.thread_id,
                direction="inbound",
                message_text=(FIXTURES / fixture_name).read_text(encoding="utf-8"),
            )
        )
        config = SupplierConfig(enable_llm_extraction=False, enable_llm_drafting=False, cache_llm_results=False)

        thread, products, supplier, _notes = analyze_supplier_thread(thread, [product], supplier, config)
        return supplier, products[0], thread
