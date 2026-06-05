# Supplier RFQ Agent Spec

## Agent Objective

Prepare a disciplined, human-approved supplier outreach and quote comparison workflow for target shed SKUs without automating message sending or purchase commitments.

## User Stories

- As an operator, I want to store supplier and product candidate records in a structured way.
- As an operator, I want pasted supplier replies converted into comparable fields and missing-info checklists.
- As an operator, I want follow-up drafts prepared but not sent automatically.
- As an operator, I want a compact RFQ pack report summarizing where each supplier thread stands.

## Inputs

- `config/supplier_config.json`
- Supplier records
- Product candidate records
- Supplier conversation text
- Optional `OPENAI_API_KEY` for extraction/drafting support

## Outputs

- RFQ templates
- Supplier thread state updates
- Pending follow-up drafts
- Supplier RFQ pack markdown reports

## Internal Workflow

1. Add supplier
2. Add product candidate
3. Add inbound or outbound message text
4. Analyze supplier thread
5. Score supplier/product fit
6. Generate pending follow-up draft if needed
7. Approve and mark manual send externally

## Data Files Used

- `data/suppliers.json`
- `data/product_candidates.json`
- `data/supplier_threads.json`
- `data/supplier_message_queue.json`
- `data/supplier_llm_cache/`

## Safety / Approval Boundaries

- No automatic supplier sending
- No automatic negotiation commitments
- No purchases or payment actions
- Human approval required before any outbound draft is treated as sent

## External Integrations

- OpenAI Responses API for extraction/drafting support when available

## Error Handling

- Missing API key falls back to deterministic/manual extraction paths where possible
- Missing supplier/thread references return explicit CLI errors
- Rejected suppliers suppress unnecessary follow-up drafting

## Future Improvements

- Better supplier comparison views
- Explicit landed-cost modeling
- Attachment-aware quote parsing
- Draft export for email/chat tools
