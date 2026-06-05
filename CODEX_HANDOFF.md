# CODEX_HANDOFF

## What This Project Is

This is a private dual-workflow repository for:

1. `Demand Listener`
   Monitors local compact shed demand and generates decision-oriented reports.
2. `Supplier RFQ Agent`
   Tracks suppliers, quote details, follow-up drafts, and sourcing readiness without auto-sending messages.

## Where To Start Reading

1. [README.md](README.md)
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md)
4. [agents/demand-listener/AGENT_SPEC.md](agents/demand-listener/AGENT_SPEC.md)
5. [agents/supplier-rfq/AGENT_SPEC.md](agents/supplier-rfq/AGENT_SPEC.md)

Then inspect:

- `shed_agent/cli.py`
- `shed_agent/routine.py`
- `shed_agent/llm_analysis.py`
- `shed_agent/generate_dashboard.py`
- `shed_agent/supplier/`

## Current Workstream Status

- Active workstream: `Demand Listener Operations and Reporting`
- Latest routine artifacts were written on `2026-06-04`
- Current recommendation: `continue watching`
- Current observation window: `2026-06-02` to `2026-06-08`
- Supplier workflow is implemented and adjacent, but not the currently hottest operational path

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
- Tests: `tests/`

## How To Continue From Here

1. Create the private GitHub repository.
2. Run the git initialization and first commit commands listed below.
3. Clone on Mac.
4. Create a venv, install dependencies, and restore `OPENAI_API_KEY`.
5. Run:

```bash
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-dashboard
python -m unittest discover -s tests
```

## What Not To Change Without Confirmation

- Supplier outbound safety model: keep it human-approved.
- Decision thresholds in `config/shed_agent_config.json` unless there is a documented business reason.
- Core JSON storage schema unless migration steps are added.
- Facebook collection behavior around login challenges and anti-bypass boundaries.
- Which generated directories are ignored by Git, unless the repo strategy changes intentionally.

## Suggested Next Codex Prompts

- `Audit the Mac setup path for this repo and add any missing bootstrap helpers.`
- `Review the supplier workflow for schema or state-transition risks before production use.`
- `Create a minimal cross-platform command runner for the common CLI tasks.`
- `Add tests around config portability and repo-local profile paths.`
- `Summarize the latest demand state from data/observations.json and reports/ if present.`
