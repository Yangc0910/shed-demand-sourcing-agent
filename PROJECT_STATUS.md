# PROJECT_STATUS

## Project

- Name: `Shed Local Demand & Sourcing Agent`
- Project type: private multi-agent operational toolkit
- Primary domain: local shed demand sensing plus supplier RFQ preparation
- Current active workstream: `Demand Listener Operations and Reporting`
- Agent-related: yes

## Completed Work

- Built a CLI entry point in `shed_agent/cli.py` covering both demand and supplier workflows.
- Implemented local demand ingestion, extraction, scoring, deduplication, and decision logic.
- Added LLM-assisted listing analysis with deterministic fallback in `shed_agent/llm_analysis.py`.
- Added local Facebook Marketplace collection and conservative import fallback.
- Implemented daily digest, weekly report, dashboard, and routine summary generation.
- Implemented supplier storage models, thread analysis, follow-up planning, scoring, and RFQ pack generation.
- Added unit test coverage across demand, supplier, dashboard, and verification paths.
- Added GitHub-ready documentation, workstream docs, and handoff docs in this migration pass.

## In-Progress Work

- Demand Listener remains in active observation mode with routine-generated outputs.
- Supplier RFQ workflow is implemented but still depends on manual operator input and manual sending.
- Cross-device GitHub backup structure has now been prepared, but the remote repository still needs to be created by the user.

## Current Implementation Status

- Demand Listener: operational for local routine/reporting.
- Supplier RFQ Agent: operational for state tracking and draft generation.
- Git repository: not originally initialized; prepared for local initialization and first commit.
- Current decision state from latest report: `continue watching`.
- Current observation window from config: `2026-06-02` through `2026-06-08`.

## Known Issues

- `config/shed_agent_config.json` previously used a Windows-specific Facebook profile path; this migration changes it to a repo-local path for cross-device use.
- Windows helper scripts in `scripts/` do not run on macOS.
- Facebook CDP/browser launch behavior is platform- and session-dependent.
- Generated logs/reports can become noisy quickly and are not suitable as Git source-of-truth files.
- The project relies on manual judgment for Facebook login challenges and supplier outbound approval.

## Important Design Decisions

- Keep code in the current top-level package layout; do not move to `src/` during migration because that would add unnecessary risk.
- Track structured JSON operational state in Git, but ignore generated caches, browser profiles, logs, and reports.
- Treat README/status/handoff/workstream docs as the durable continuation layer across devices.
- Keep supplier outreach human-approved; do not automate sending or commitments.
- Preserve cross-platform Python usage in docs even though some helper scripts remain Windows-only.

## Next Recommended Tasks

1. Create the GitHub repository and add the remote.
2. Initialize git locally, commit the GitHub-ready baseline, and push `main`.
3. Clone on the Mac and verify setup using `python -m shed_agent.cli decision-check`.
4. Add a small Mac helper script or `Makefile` for common commands if cross-device usage becomes frequent.
5. Optionally split demand and supplier docs further if the repo grows.

## Risks Or Blockers

- No GitHub remote exists yet, so backup/sync is not complete until the first push happens.
- Facebook local session state does not transfer across devices and must be re-established per machine.
- If `.env` or shell profile variables are not recreated on Mac, LLM analysis will fall back to deterministic mode.
- Operational JSON state is useful to sync, but it may contain sensitive business notes; repo visibility should remain private.
