# Supplier RFQ Agent

Human-approved sourcing support agent for compact shed suppliers and product candidates.

## Role

- Track supplier records and product candidates
- Parse inbound quote/reply details
- Score supplier fit and risk
- Create initial RFQ and follow-up drafts
- Maintain a manual approval queue instead of auto-sending

## Main Entry Points

- `shed_agent/supplier/`
- `shed_agent/cli.py`

## State

- `data/suppliers.json`
- `data/product_candidates.json`
- `data/supplier_threads.json`
- `data/supplier_message_queue.json`
- `config/supplier_config.json`
