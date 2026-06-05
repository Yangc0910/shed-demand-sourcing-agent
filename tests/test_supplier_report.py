import unittest

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessageDraft, SupplierThread
from shed_agent.supplier.report import generate_supplier_rfq_pack


class SupplierReportTests(unittest.TestCase):
    def test_report_contains_required_sections(self):
        supplier = Supplier(supplier_name="Example Supplier", platform="Made-in-China")
        product = ProductCandidate(
            supplier_id=supplier.supplier_id,
            product_name="6x5 Vertical Shed",
            product_type="6x5_vertical",
            unit_price=280,
            moq=10,
        )
        thread = SupplierThread(supplier_id=supplier.supplier_id, product_ids=[product.product_id])
        draft = SupplierMessageDraft(
            thread_id=thread.thread_id,
            supplier_id=supplier.supplier_id,
            purpose="follow_up",
            draft_text_chinese="您好",
            draft_text_english="Hello",
        )

        report = generate_supplier_rfq_pack([supplier], [product], [thread], [draft], SupplierConfig())

        self.assertIn("供应商询价包", report)
        self.assertIn("决策总览", report)
        self.assertIn("供应商短名单", report)
        self.assertIn("淘汰与暂缓候选", report)
        self.assertIn("供应商沟通状态", report)
        self.assertIn("待审核消息草稿", report)
        self.assertIn("供应商信心评分", report)
        self.assertIn("候选建议", report)
        self.assertIn("系统不会自动发送供应商消息", report)
