# Shed Local Demand & Sourcing Agent

Private multi-agent toolkit for evaluating local shed demand in Greater Boston and preparing a human-approved supplier RFQ workflow for compact resin/plastic sheds.

## Project Purpose

This repository is the working source of truth for two connected agent workflows:

1. `Demand Listener`
   Tracks local demand signals, scores listings, generates digest/report/dashboard outputs, and recommends whether to keep watching, begin supplier research, or stop.
2. `Supplier RFQ Agent`
   Tracks suppliers, product candidates, inbound/outbound thread state, structured quote extraction, and human-approved follow-up drafts.

The current active operational workstream is documented in [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md).

## High-Level Architecture

```text
CLI
  -> shed_agent.cli
     -> demand listener modules
        -> ingest / extract / deduplicate / score / llm_analysis / decision
        -> reports: daily digest / weekly report / dashboard / routine summary
     -> supplier modules
        -> suppliers / products / threads / message queue / scoring / report
JSON storage
  -> data/observations.json
  -> data/suppliers.json
  -> data/product_candidates.json
  -> data/supplier_threads.json
  -> data/supplier_message_queue.json
Config
  -> config/shed_agent_config.json
  -> config/supplier_config.json
```

## Main Features

- Local demand observation storage and scoring for `4x6_horizontal` and `6x5_vertical`
- Craigslist/watchlist/manual snippet ingestion
- Local Facebook Marketplace collection with manual-login-safe behavior
- LLM-assisted listing interpretation with deterministic fallback
- Daily digest, weekly report, decision check, and HTML dashboard generation
- Supplier + product + thread state tracking
- RFQ template generation and human-approved follow-up queue
- Local scheduled routine support on Windows

## Repository Layout

```text
project-root/
  README.md
  PROJECT_STATUS.md
  CODEX_HANDOFF.md
  .gitignore
  .env.example
  docs/
    architecture.md
    mac-setup.md
  workstreams/
    demand-listener-ops-and-reporting.md
  agents/
    demand-listener/
      README.md
      AGENT_SPEC.md
      TASKS.md
    supplier-rfq/
      README.md
      AGENT_SPEC.md
      TASKS.md
  config/
  data/
  examples/
  scripts/
  shed_agent/
  tests/
```

No code directories were moved in this migration pass. That keeps the current implementation stable while adding GitHub-ready structure around it.

## Setup

### Requirements

- Python `3.10+`
- Git
- Optional: Playwright browser runtime for Facebook collection
- Optional: `OPENAI_API_KEY` for LLM-based analysis and drafting

### Create a Virtual Environment

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
python -m playwright install chromium
```

macOS / zsh:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m playwright install chromium
```

### Environment Variables

Copy `.env.example` to `.env` if you want a local env file.

```text
OPENAI_API_KEY=
```

## How To Run Locally

Cross-platform CLI examples:

```bash
python -m shed_agent.cli --help
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-daily-digest
python -m shed_agent.cli generate-dashboard
python -m shed_agent.cli generate-supplier-report
```

Windows-specific scheduled routine:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\scripts\run_routine.ps1"
```

## Key Data And Outputs

Tracked operational state:

- `data/observations.json`
- `data/suppliers.json`
- `data/product_candidates.json`
- `data/supplier_threads.json`
- `data/supplier_message_queue.json`

Generated artifacts that are intentionally ignored by Git:

- `logs/`
- `reports/`
- `.local/`
- `data/llm_cache/`
- `data/supplier_llm_cache/`

## Dependencies

Declared in [pyproject.toml](pyproject.toml):

- `playwright>=1.44.0`

The code also uses standard-library HTTP/JSON tooling and optional OpenAI API access via direct HTTP requests.

## Current Status

See:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [CODEX_HANDOFF.md](CODEX_HANDOFF.md)
- [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md)

As of `2026-06-04`, the demand routine is producing daily digest, decision check, routine summary, and dashboard outputs successfully. The current recommendation remains `continue watching`.

## Testing

```bash
python -m unittest discover -s tests
```

## Important Notes

- Facebook collection is best-effort and depends on a valid local logged-in session.
- Supplier messaging remains human-approved; the project does not auto-send supplier outreach.
- The repository is intended to sync code, docs, and agent state across Windows and Mac, but Windows helper scripts remain Windows-only by design.
