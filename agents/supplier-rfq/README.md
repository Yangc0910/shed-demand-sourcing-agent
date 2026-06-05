# Supplier RFQ & Communication Agent

Private supplier-side workflow for compact resin/plastic shed sourcing.

## What It Does

- Stores supplier profiles and product candidates.
- Generates Chinese and English RFQ templates.
- Queues outbound RFQ/follow-up drafts for human approval.
- Accepts pasted supplier replies.
- Extracts quote fields with optional LLM support and deterministic fallback.
- Detects missing critical information.
- Generates Chinese follow-up drafts.
- Scores supplier/product candidates.
- Generates a Chinese Supplier RFQ Pack report.

## What It Does Not Do

- It does not browse supplier platforms automatically.
- It does not send messages automatically.
- It does not place orders.
- It does not process payments.
- It does not expose a public UI.

## Main Entry Points

- `shed_agent/supplier/`
- `shed_agent/cli.py`
- `config/supplier_config.json`

## Runtime State

- `data/suppliers.json`
- `data/product_candidates.json`
- `data/supplier_threads.json`
- `data/supplier_message_queue.json`
- `data/supplier_llm_cache/`

These files are private local runtime state and are ignored by Git by default.

## First Real Supplier Flow

```bash
shed-agent add-supplier --name "SUPPLIER_NAME" --platform "Alibaba" --url "PRODUCT_OR_COMPANY_URL"
shed-agent add-product-candidate --supplier-id SUPPLIER_ID --name "4x6 horizontal resin shed" --product-type 4x6_horizontal --url "PRODUCT_URL"
shed-agent generate-rfq-template --product-type 4x6_horizontal --queue-for-supplier SUPPLIER_ID
shed-agent list-message-queue
shed-agent approve-message-draft --draft-id DRAFT_ID
shed-agent mark-message-sent-manually --draft-id DRAFT_ID --language chinese
```

After the supplier replies:

```bash
shed-agent add-supplier-message --supplier-id SUPPLIER_ID --text-file supplier-reply.txt
shed-agent analyze-supplier-thread --thread-id THREAD_ID
shed-agent generate-follow-up-draft --thread-id THREAD_ID
shed-agent generate-supplier-report --out reports/supplier-rfq-pack.md
```
