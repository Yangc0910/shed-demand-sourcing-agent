# Shed Local Demand & Sourcing Agent

Private multi-agent toolkit for evaluating local compact-shed demand in Greater Boston and preparing a cautious supplier RFQ workflow for small-batch sourcing.

## Project Purpose

This repository is the GitHub-ready source of truth for:

- code
- project status
- active workstream status
- next actions
- agent instructions
- portable setup notes for Windows and Mac

The project currently contains two related agent lanes:

1. `Demand Listener`
   Monitors local market signals, scores demand quality, and generates decision-oriented artifacts.
2. `Supplier RFQ Agent`
   Tracks suppliers, product candidates, reply analysis, and human-approved draft messaging.

The currently active workstream is [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md).

## High-Level Architecture

```text
CLI
  -> shed_agent.cli
     -> demand listener modules
        -> ingest / extract / deduplicate / score / llm_analysis / decision
        -> outputs: daily digest / weekly report / dashboard / routine summary
     -> supplier modules
        -> suppliers / products / threads / queue / scoring / report

Tracked state
  -> data/observations.json
  -> data/suppliers.json
  -> data/product_candidates.json
  -> data/supplier_threads.json
  -> data/supplier_message_queue.json

Config
  -> config/shed_agent_config.json
  -> config/supplier_config.json

Documentation
  -> PROJECT_STATUS.md
  -> CODEX_HANDOFF.md
  -> workstreams/
  -> agents/
  -> docs/
```

## Main Features

- local demand observation storage and scoring
- Craigslist RSS, watchlist, local snippet, and conservative Facebook capture flows
- LLM-assisted interpretation with fallback behavior
- daily digest, weekly report, dashboard, and decision-check generation
- supplier, product, thread, and message-queue tracking
- bilingual RFQ generation and follow-up planning
- local routine wrappers for Windows and Mac/Linux

## Repository Layout

```text
project-root/
  README.md
  PROJECT_STATUS.md
  CODEX_HANDOFF.md
  .gitignore
  .gitattributes
  .env.example
  docs/
    architecture.md
    cross-device-sync.md
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

No source files were moved during this migration pass. The package stays in `shed_agent/` to avoid unnecessary churn before backup and cross-device sync.

## Setup

### Requirements

- Python `3.10+`
- Git
- optional Playwright Chromium runtime
- optional `OPENAI_API_KEY`

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
py -m playwright install chromium
```

### Mac / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m playwright install chromium
```

Optional local env file:

```text
OPENAI_API_KEY=
```

## How To Run Locally

Cross-platform CLI:

```bash
python -m shed_agent.cli --help
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-daily-digest
python -m shed_agent.cli generate-dashboard
python -m shed_agent.cli generate-supplier-report
python -m unittest discover -s tests
```

Windows routine wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\scripts\run_routine.ps1"
```

Mac/Linux routine wrapper:

```bash
bash ./scripts/run_routine.sh
```

## Dependencies

Declared in `pyproject.toml`:

- `playwright>=1.44.0`

LLM-assisted analysis additionally requires `OPENAI_API_KEY`.

## Current Status

- Demand Listener is the currently active operational lane.
- Latest demand artifacts indicate `continue watching`.
- Current configured observation window is `2026-06-02` through `2026-06-08`.
- Supplier RFQ code is implemented and test-covered, but the checked-in supplier JSON state is currently empty.
- The current automated test baseline passes.

See:

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [CODEX_HANDOFF.md](CODEX_HANDOFF.md)
- [docs/cross-device-sync.md](docs/cross-device-sync.md)

## Important Notes

- Keep the GitHub repo private.
- Do not commit `.local/`, browser session state, logs, reports, or caches.
- Supplier outreach remains human-approved only.
- Windows helper scripts remain Windows-specific; the Python CLI itself is portable.
