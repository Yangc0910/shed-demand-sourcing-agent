# Project Status

Last updated: 2026-06-05

## Project

- Name: `Shed Local Demand & Sourcing Agent`
- Recommended GitHub repo name: `shed-demand-sourcing-agent`
- Agent-related: Yes
- Current active workstream: `Demand Listener Operations and Reporting`

## Completed Work

- Implemented a unified CLI in `shed_agent/cli.py` for both demand and supplier workflows.
- Implemented local demand observation ingestion, extraction, scoring, deduplication, and decision logic.
- Implemented daily digest, weekly report, dashboard, and routine summary outputs.
- Implemented conservative Facebook Marketplace collection/import support.
- Implemented supplier storage, RFQ template generation, thread analysis, follow-up drafting, and supplier RFQ reporting.
- Added GitHub-ready documentation, handoff docs, workstream docs, and agent-specific documentation.
- Added a Mac/Linux routine wrapper at `scripts/run_routine.sh`.
- Verified the current baseline with `73` passing tests.

## In-Progress Work

- Demand Listener remains in active listening mode rather than sourcing escalation mode.
- Supplier RFQ workflow is implemented but still relies on manual operator input and manual sending.
- GitHub sync is prepared locally, but there is still no remote configured.

## Current Implementation Status

### Demand Listener

- Operational and generating current reports.
- Latest decision state remains `continue watching`.
- Current observation window is `2026-06-02` through `2026-06-08`.
- `data/observations.json` currently contains `69` observations.

### Supplier RFQ Agent

- Operational in code and covered by tests.
- Current checked-in supplier JSON files are empty and ready for real data entry.
- Existing supplier pack artifacts in `reports/` should be treated as generated examples, not canonical state.

## Known Issues

- Facebook collection remains session- and platform-dependent.
- Windows PowerShell helper scripts do not run on Mac.
- Generated logs and reports can become noisy and are not good git source-of-truth files.
- Mac scheduling is not automated yet.

## Important Design Decisions

- Keep code in the existing `shed_agent/` layout rather than moving to `src/`.
- Treat top-level docs plus `workstreams/` and `agents/` as the durable continuation layer across devices.
- Keep supplier outreach human-approved only.
- Use a repo-local ignored browser profile path for Facebook collection: `.local/playwright/facebook-profile`.
- Keep browser state, logs, reports, and caches out of git.

## Next Recommended Tasks

1. Create the private GitHub repository.
2. Add the remote and push `main`.
3. Clone on the Mac and verify setup with tests.
4. Decide whether `data/observations.json` should remain a living tracked state file or be periodically snapshotted.
5. If supplier work becomes active, start populating the supplier JSON files with real records.

## Risks Or Blockers

- Backup/sync is incomplete until the first GitHub push happens.
- Local browser session state does not transfer across devices.
- If `OPENAI_API_KEY` is not restored on Mac, LLM-assisted flows fall back or degrade.
- Repo visibility should stay private because tracked state may still contain sensitive business context.
