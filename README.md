# Shed Local Demand & Sourcing Agent

Private local workflow for validating compact resin/plastic shed demand around Greater Boston and managing early China supplier RFQ conversations. The project is CLI-first, file-backed, and intentionally private: it does not automatically contact suppliers, place orders, process payments, or publish a public UI.

## Current Workstreams

- **Workstream 01 - Demand Listener**: monitors and analyzes local compact shed demand signals from manual entries, configured URLs, Craigslist RSS, retail comparables, and optional Facebook Marketplace collection.
- **Workstream 02 - Supplier RFQ / China Sourcing**: manages supplier records, product candidates, bilingual RFQ drafts, supplier replies, missing-information follow-ups, confidence scoring, and a Chinese Supplier RFQ Pack report.

## Architecture

- `shed_agent/`: Python package and CLI entry point.
- `shed_agent/supplier/`: supplier RFQ and communication workflow modules.
- `config/`: portable JSON configuration templates for demand and supplier workflows.
- `tests/`: unit and end-to-end workflow tests.
- `scripts/`: Windows helper scripts for routine local runs.
- `workstreams/`: workstream-level project memory for GitHub/Codex handoff.
- `agents/`: agent-specific instructions, specs, and task lists.
- `data/`, `logs/`, `reports/`, `.local/`: local runtime state. These are ignored by Git by default because they can contain private marketplace data, supplier conversations, browser sessions, generated reports, and caches.

There is no destructive file move planned. The package currently lives in `shed_agent/` rather than `src/`; keeping it in place avoids unnecessary churn.

## Setup

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
py -m playwright install chromium
```

Mac or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m playwright install chromium
```

`OPENAI_API_KEY` is optional. If it is not set, the LLM-assisted analysis and supplier reply extraction use deterministic fallback behavior where available.

## Common Commands

Demand Listener:

```bash
shed-agent add-observation --text "Suncast 4x6 resin shed, $450, Lexington"
shed-agent analyze-observations
shed-agent generate-daily-digest --out reports/daily-digest.md
shed-agent generate-dashboard --out reports/dashboard.html
shed-agent decision-check
```

Supplier RFQ workflow:

```bash
shed-agent add-supplier --name "Example Plastics" --platform "Alibaba" --url "https://example.com"
shed-agent add-product-candidate --supplier-id SUPPLIER_ID --name "4x6 horizontal resin shed" --product-type 4x6_horizontal
shed-agent generate-rfq-template --product-type 4x6_horizontal --queue-for-supplier SUPPLIER_ID
shed-agent add-supplier-message --supplier-id SUPPLIER_ID --text-file supplier-reply.txt
shed-agent analyze-supplier-thread --thread-id THREAD_ID
shed-agent generate-follow-up-draft --thread-id THREAD_ID
shed-agent list-message-queue
shed-agent approve-message-draft --draft-id DRAFT_ID
shed-agent mark-message-sent-manually --draft-id DRAFT_ID --language chinese
shed-agent generate-supplier-report --out reports/supplier-rfq-pack.md
```

No supplier message is sent automatically. Draft approval and manual sending are explicit separate steps.

## Current Status

Workstream 01 is functional as a private demand-listening workflow. Workstream 02 has a first automation-ready Supplier RFQ & Communication Agent with tested scenario coverage and a Chinese report/dashboard. See:

- [Project Status](PROJECT_STATUS.md)
- [Codex Handoff](CODEX_HANDOFF.md)
- [Workstream 02](workstreams/workstream-02-supplier-rfq-china-sourcing.md)
- [Supplier Agent](agents/supplier-rfq-communication-agent/README.md)
- [Demand Listener Agent](agents/demand-listener/README.md)

## Cross-Device Notes

GitHub should be the source of truth for code and documentation. Runtime data should remain local on each device. After cloning on a Mac, recreate `.venv`, install dependencies, and configure any local paths in `config/shed_agent_config.json` before running browser-based collection.
