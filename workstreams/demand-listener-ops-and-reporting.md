# Workstream: Demand Listener Operations and Reporting

## Workstream Objective

Keep the local shed demand listener operational as a daily decision-support system, with stable report generation and enough documentation to continue on either Windows or Mac.

## Scope

- Demand observation ingestion and scoring
- LLM-assisted or fallback verification
- Daily digest, decision check, dashboard, and routine summaries
- GitHub-ready handoff and cross-device continuation support

## Why This Is The Current Workstream

- The most recent artifacts in the repository are routine summaries, daily digests, decision checks, and dashboard outputs dated `2026-06-04`.
- The latest recommendation state and operational heartbeat are driven by this workflow.
- Supplier RFQ code exists and is usable, but it is not the most recently active operational lane.

## Agent Name

- `Demand Listener`

## Agent Purpose

Monitor local demand signals for compact sheds around Greater Boston and recommend whether the market is still worth watching or ready for deeper sourcing work.

## Inputs

- `data/observations.json`
- `config/shed_agent_config.json`
- Manual snippets and observations
- Optional Craigslist RSS and watchlist URLs
- Optional local Facebook capture/collector input
- Optional `OPENAI_API_KEY`

## Outputs

- `reports/daily-digest-YYYY-MM-DD.md`
- `reports/decision-check-YYYY-MM-DD.md`
- `reports/dashboard.html`
- `reports/routine-summary-YYYY-MM-DD.json`
- `reports/routine-summary-YYYY-MM-DD.md`

## Tools Used

- Python CLI via `python -m shed_agent.cli`
- Playwright for Facebook collection
- OpenAI Responses API for structured analysis when enabled
- Windows Task Scheduler wrapper scripts for local automation on Windows

## Storage / Data Model

- Main state file: `data/observations.json`
- LLM cache: `data/llm_cache/`
- Generated artifacts: `logs/`, `reports/`

## Files Changed Or Created In This Migration Pass

- `README.md`
- `PROJECT_STATUS.md`
- `CODEX_HANDOFF.md`
- `.env.example`
- `.gitignore`
- `docs/architecture.md`
- `docs/mac-setup.md`
- `workstreams/demand-listener-ops-and-reporting.md`
- `agents/demand-listener/*`
- `agents/supplier-rfq/*`
- `config/shed_agent_config.json`

## Key Decisions

- Treat this as the active workstream for handoff purposes.
- Keep generated reports out of Git; use structured data and docs as the portable source of truth.
- Use a repo-local Facebook profile path instead of a Windows-only `%LOCALAPPDATA%` path.
- Do not move package layout or operational files during migration.

## Current Status

- Operational and producing current reports
- Latest routine status: success on `2026-06-04`
- Current recommendation: `continue watching`
- Current 7-day observation window: `2026-06-02` to `2026-06-08`

## Next Steps

1. Initialize git and create the first local commit.
2. Create the private GitHub repository and push `main`.
3. Clone on Mac and validate setup.
4. Optionally add a small cross-platform bootstrap helper for common CLI commands.

## Open Questions

- Should operational JSON data be fully versioned long-term, or periodically snapshotted instead?
- Should demand and supplier workflows remain in one repo as they grow?
- Do you want a Mac-native scheduled routine path later, or only manual Mac continuation?

## Connections To Other Workstreams

- Upstream/adjacent: `Supplier RFQ Agent`
- Trigger relationship: stronger demand signals can justify more active supplier follow-up

## CLI Commands

```bash
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-daily-digest
python -m shed_agent.cli generate-dashboard
python -m shed_agent.cli routine
```

## Testing Approach

- Unit tests under `tests/`
- Manual validation through routine outputs in `reports/`

## Failure Modes

- Missing `OPENAI_API_KEY` causes fallback-only analysis
- Facebook session/login challenge blocks collector progress
- Platform-specific helper scripts do not run on Mac
- Generated outputs can drift from docs if not regenerated after major logic changes

## Manual Approval Steps

- Facebook login/challenge handling is manual
- Any business decision beyond `continue watching` still needs human judgment
