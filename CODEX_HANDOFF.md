# Codex Handoff

## What This Project Is

This is a private local agent project for two connected jobs:

- Listen for local demand for compact resin/plastic sheds near Greater Boston.
- Manage early-stage China supplier RFQ conversations for 4x6 horizontal and 6x5 vertical resin/plastic sheds.

The current active workstream is **Workstream 02: Supplier RFQ / China Sourcing**.

## Where To Start Reading

1. `README.md`
2. `PROJECT_STATUS.md`
3. `workstreams/workstream-02-supplier-rfq-china-sourcing.md`
4. `agents/supplier-rfq-communication-agent/AGENT_SPEC.md`
5. `shed_agent/cli.py`
6. `shed_agent/supplier/`

For Workstream 01, read:

1. `workstreams/workstream-01-demand-listener.md`
2. `agents/demand-listener/AGENT_SPEC.md`
3. `shed_agent/facebook_marketplace.py`
4. `shed_agent/routine.py`

## Current Workstream Status

Workstream 02 has a first working version. It can add suppliers, add product candidates, generate bilingual RFQs, queue drafts, ingest pasted supplier replies, analyze threads, detect missing information, generate follow-up drafts, approve drafts, mark manually sent messages, score candidates, and generate a Chinese Supplier RFQ Pack report.

The workflow has been validated against three realistic supplier scenarios: strong candidate, incomplete information, and high-risk/not suitable supplier.

## Important Files

- `shed_agent/cli.py`: CLI commands for both workstreams.
- `shed_agent/supplier/models.py`: supplier, product, thread, message, draft, extraction, follow-up, and score data models.
- `shed_agent/supplier/rfq.py`: bilingual RFQ template generation.
- `shed_agent/supplier/llm_extract.py`: LLM extraction with deterministic fallback.
- `shed_agent/supplier/followup.py`: missing information and follow-up question generation.
- `shed_agent/supplier/message_queue.py`: human-approved draft queue.
- `shed_agent/supplier/scoring.py`: deterministic confidence score.
- `shed_agent/supplier/report.py`: Chinese Supplier RFQ Pack report.
- `tests/test_supplier_scenarios.py`: end-to-end supplier workflow validation.

## How To Continue

- Keep changes scoped to the active workstream unless the user explicitly asks otherwise.
- For supplier work, prefer adding focused tests around the full CLI/user flow.
- If adding real supplier data, treat it as local runtime data and keep it out of Git.
- Use `generate-supplier-report` to produce the decision view after supplier replies are analyzed.

## Do Not Change Without Confirmation

- Do not modify Demand Listener collector logic unless absolutely necessary.
- Do not automate supplier browsing.
- Do not send supplier messages automatically.
- Do not place orders, implement payment, or add public UI.
- Do not commit private live data from `data/`, `logs/`, `.local/`, or generated `reports/`.
- Do not destructively move project files without explaining the migration first.

## Suggested Next Codex Prompts

- "Use the Supplier RFQ Agent to enter my first real supplier. Keep all data local."
- "Review the first supplier reply and generate a Chinese follow-up draft."
- "Run the supplier report and tell me which supplier is worth continuing."
- "After cloning on Mac, verify setup and tests without changing Workstream 01 collector logic."
