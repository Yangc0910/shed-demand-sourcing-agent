from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessageDraft, SupplierThread


DEFAULT_SUPPLIERS_PATH = Path("data/suppliers.json")
DEFAULT_PRODUCTS_PATH = Path("data/product_candidates.json")
DEFAULT_THREADS_PATH = Path("data/supplier_threads.json")
DEFAULT_MESSAGE_QUEUE_PATH = Path("data/supplier_message_queue.json")

T = TypeVar("T")


def load_suppliers(path: Path = DEFAULT_SUPPLIERS_PATH) -> list[Supplier]:
    return _load(path, Supplier)


def save_suppliers(items: list[Supplier], path: Path = DEFAULT_SUPPLIERS_PATH) -> None:
    _save(path, items)


def load_product_candidates(path: Path = DEFAULT_PRODUCTS_PATH) -> list[ProductCandidate]:
    return _load(path, ProductCandidate)


def save_product_candidates(items: list[ProductCandidate], path: Path = DEFAULT_PRODUCTS_PATH) -> None:
    _save(path, items)


def load_supplier_threads(path: Path = DEFAULT_THREADS_PATH) -> list[SupplierThread]:
    return _load(path, SupplierThread)


def save_supplier_threads(items: list[SupplierThread], path: Path = DEFAULT_THREADS_PATH) -> None:
    _save(path, items)


def load_message_queue(path: Path = DEFAULT_MESSAGE_QUEUE_PATH) -> list[SupplierMessageDraft]:
    return _load(path, SupplierMessageDraft)


def save_message_queue(items: list[SupplierMessageDraft], path: Path = DEFAULT_MESSAGE_QUEUE_PATH) -> None:
    _save(path, items)


def add_supplier(item: Supplier, path: Path = DEFAULT_SUPPLIERS_PATH) -> Supplier:
    items = load_suppliers(path)
    items.append(item)
    save_suppliers(items, path)
    return item


def add_product_candidate(item: ProductCandidate, path: Path = DEFAULT_PRODUCTS_PATH) -> ProductCandidate:
    items = load_product_candidates(path)
    items.append(item)
    save_product_candidates(items, path)
    return item


def add_supplier_thread(item: SupplierThread, path: Path = DEFAULT_THREADS_PATH) -> SupplierThread:
    items = load_supplier_threads(path)
    items.append(item)
    save_supplier_threads(items, path)
    return item


def add_message_draft(item: SupplierMessageDraft, path: Path = DEFAULT_MESSAGE_QUEUE_PATH) -> SupplierMessageDraft:
    items = load_message_queue(path)
    items.append(item)
    save_message_queue(items, path)
    return item


def _load(path: Path, cls: type[T]) -> list[T]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [cls.from_dict(item) for item in data]


def _save(path: Path, items: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([item.to_dict() for item in items], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
