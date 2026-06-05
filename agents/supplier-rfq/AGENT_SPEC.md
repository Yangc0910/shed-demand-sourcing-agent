# Agent Spec: Supplier RFQ & Communication Agent

## Objective

Help the user manage China supplier RFQ conversations for compact resin/plastic sheds and decide which suppliers are worth continuing with for a first 5-10 unit inventory batch.

## User Stories

- As the user, I can add a supplier from Alibaba, Made-in-China, 1688, Global Sources, email, or another source.
- As the user, I can add one or more product candidates for that supplier.
- As the user, I can generate a bilingual RFQ and queue it without sending it.
- As the user, I can paste a supplier reply and have it converted into structured quote fields.
- As the user, I can see what information is missing before I continue negotiation.
- As the user, I can review a natural Chinese follow-up draft before manually sending it.
- As the user, I can open one Chinese report and quickly see continue, watch, or pass recommendations.

## Inputs

- Supplier platform, name, URL, contact notes, location, export experience.
- Product type, size, dimensions, material, MOQ, pricing, sample cost, lead time, carton data, weight, shipping estimate, support assets, branding, packaging notes, risk notes.
- Raw supplier reply text pasted manually.
- Supplier config thresholds in `config/supplier_config.json`.

## Outputs

- `Supplier` records.
- `ProductCandidate` records.
- `SupplierThread` conversation records.
- `SupplierMessageDraft` records.
- Extracted quote fields and missing-information lists.
- Chinese and English RFQ/follow-up drafts.
- Supplier confidence score and recommendation.
- Chinese Supplier RFQ Pack report.

## Internal Workflow

1. Add supplier.
2. Add product candidate.
3. Generate RFQ template.
4. Queue RFQ draft for supplier.
5. User manually sends approved draft.
6. User pastes supplier reply.
7. Analyze thread and update product/supplier fields.
8. Detect missing information and risks.
9. Generate follow-up draft if needed.
10. Produce Supplier RFQ Pack report.

## Data Files Used

- `data/suppliers.json`
- `data/product_candidates.json`
- `data/supplier_threads.json`
- `data/supplier_message_queue.json`
- `data/supplier_llm_cache/`

These are runtime/private files and should stay out of Git.

## Safety And Approval Boundaries

- Outbound mode is human-approved.
- Draft approval does not send a message.
- Marking a draft sent only records that the user manually sent it elsewhere.
- No automatic supplier browsing, automatic messages, orders, payments, or public UI.

## External Integrations

- Optional OpenAI API for structured extraction and drafting when `OPENAI_API_KEY` is available.
- No direct supplier-platform API integration.

## Error Handling

- Missing supplier/thread/draft IDs return clear not-found messages.
- Missing API key falls back to deterministic extraction/drafting where available.
- Rejected suppliers do not receive queued follow-up drafts.
- Duplicate pending drafts are avoided.

## Future Improvements

- Improve CLI ergonomics for selecting supplier/thread IDs.
- Add sanitized sample supplier data for demos.
- Add optional export to CSV/XLSX for supplier comparison.
- Add Mac-specific browser setup notes if Workstream 01 is used heavily on Mac.
