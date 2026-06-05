# Codex Handoff

## What This Project Is

This is a private dual-agent repository for:

1. local compact-shed demand monitoring
2. early supplier RFQ workflow support

The repo is meant to be the durable continuation layer across Windows and Mac, even if Codex conversation history does not sync cleanly.

## Where To Start Reading

1. `README.md`
2. `PROJECT_STATUS.md`
3. `workstreams/demand-listener-ops-and-reporting.md`
4. `agents/demand-listener/AGENT_SPEC.md`
5. `agents/supplier-rfq/AGENT_SPEC.md`
6. `shed_agent/cli.py`

## Current Workstream Status

- Active workstream: `Demand Listener Operations and Reporting`
- Latest operational artifacts are dated `2026-06-04`
- Latest recommendation: `continue watching`
- Current observation window: `2026-06-02` to `2026-06-08`
- Supplier RFQ remains implemented and ready, but is not the hottest operational lane right now

## Important Files

- Demand config: `config/shed_agent_config.json`
- Supplier config: `config/supplier_config.json`
- Demand state: `data/observations.json`
- Supplier state:
  - `data/suppliers.json`
  - `data/product_candidates.json`
  - `data/supplier_threads.json`
  - `data/supplier_message_queue.json`
- Main entry point: `shed_agent/cli.py`
- Scheduled routine: `shed_agent/routine.py`
- Mac sync notes: `docs/cross-device-sync.md`

## How To Continue From Here

1. Push this repo to private GitHub.
2. Clone it on the Mac.
3. Create a virtual environment and install dependencies.
4. Restore `OPENAI_API_KEY` if needed.
5. Run tests first.
6. Continue from the current workstream doc rather than inferring state from `reports/`.

## What Not To Change Without Confirmation

- Supplier outbound safety model
- Demand decision thresholds without business context
- Browser challenge/login boundaries
- The decision to keep runtime outputs out of git
- The current package layout unless there is a concrete packaging problem

## Suggested Next Codex Prompts

- `Audit this repo after Mac clone and verify setup, tests, and routine commands.`
- `Add a Mac-native scheduled routine path without changing Windows behavior.`
- `Review whether data/observations.json should stay tracked or be archived periodically.`
- `Seed the supplier workflow with real supplier records and produce the first tracked RFQ pack.`
