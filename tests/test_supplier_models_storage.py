import tempfile
import unittest
from pathlib import Path

from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessage, SupplierMessageDraft, SupplierThread
from shed_agent.supplier.storage import (
    load_message_queue,
    load_product_candidates,
    load_supplier_threads,
    load_suppliers,
    save_message_queue,
    save_product_candidates,
    save_supplier_threads,
    save_suppliers,
)


class SupplierModelsStorageTests(unittest.TestCase):
    def test_supplier_product_thread_and_message_queue_round_trip(self):
        supplier = Supplier(supplier_name="Example Supplier", platform="Alibaba")
        product = ProductCandidate(supplier_id=supplier.supplier_id, product_name="4x6 Shed", product_type="4x6_horizontal")
        thread = SupplierThread(supplier_id=supplier.supplier_id, product_ids=[product.product_id])
        thread.messages.append(
            SupplierMessage(thread_id=thread.thread_id, direction="inbound", message_text="MOQ 10")
        )
        draft = SupplierMessageDraft(
            thread_id=thread.thread_id,
            supplier_id=supplier.supplier_id,
            purpose="follow_up",
            draft_text_chinese="您好",
            draft_text_english="Hello",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_suppliers([supplier], root / "suppliers.json")
            save_product_candidates([product], root / "products.json")
            save_supplier_threads([thread], root / "threads.json")
            save_message_queue([draft], root / "queue.json")

            self.assertEqual(load_suppliers(root / "suppliers.json")[0].supplier_name, "Example Supplier")
            self.assertEqual(load_product_candidates(root / "products.json")[0].product_type, "4x6_horizontal")
            self.assertEqual(load_supplier_threads(root / "threads.json")[0].messages[0].message_text, "MOQ 10")
            self.assertEqual(load_message_queue(root / "queue.json")[0].approval_status, "pending")
