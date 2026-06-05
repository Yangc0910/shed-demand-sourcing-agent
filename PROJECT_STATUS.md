# Project Status

Last updated: 2026-06-05

## Completed

- Built the core private CLI workflow for local compact shed demand monitoring.
- Added manual observation, local snippet, Craigslist RSS, watchlist, retail comparable, Facebook Marketplace capture/import, scoring, deduplication, LLM fallback, digest, dashboard, weekly report, routine run, and decision-check flows.
- Built Workstream 02 Supplier RFQ & Communication Agent for compact resin/plastic sheds.
- Added supplier data model, product candidates, supplier threads, message drafts, bilingual RFQ templates, supplier reply extraction, follow-up generation, deterministic scoring, and Supplier RFQ Pack reporting.
- Ran end-to-end supplier validation scenarios for strong, incomplete, and high-risk suppliers.
- Converted the supplier report/dashboard output to Chinese.
- Added GitHub/Codex handoff documentation and agent-specific documentation.

## In Progress

- Real supplier onboarding is ready to start manually.
- GitHub backup is prepared, but the folder is not yet connected to a remote repository.
- Cross-device continuation is documented; Mac setup still needs to be tested after clone.

## Known Issues

- The project was not a Git repository before this migration preparation.
- `data/`, `logs/`, `reports/`, `.local/`, browser profiles, and LLM caches contain local runtime state and should not be committed.
- Some Workstream 01 helper scripts are Windows PowerShell-specific.
- `config/shed_agent_config.json` currently includes a Windows-style `%LOCALAPPDATA%` browser profile path for Facebook collection.
- Facebook Marketplace collection is inherently session/browser dependent and may require manual login or challenge handling on each device.

## Important Design Decisions

- Keep Workstream 01 Demand Listener collector logic stable unless a fix is absolutely necessary.
- Keep Supplier RFQ as a private internal workflow with human approval before any outbound message.
- Do not automatically browse Alibaba, Made-in-China, 1688, or Global Sources.
- Do not send supplier messages automatically.
- Do not implement ordering, payment, or public UI.
- Keep live data local and commit source code, tests, config templates, and documentation to GitHub.
- Keep `shed_agent/` as the package root for now rather than moving code into `src/`.

## Next Recommended Tasks

- Initialize Git locally after reviewing ignored files.
- Create a private GitHub repository named `shed-local-demand-sourcing-agent` or `supplier-rfq-agent`.
- Commit code and documentation, then add the GitHub remote and push.
- On the MacBook Air, clone the repository, create a fresh virtual environment, install dependencies, and run tests.
- Start the first real supplier workflow by adding one supplier and one product candidate, then queue the RFQ draft for manual review.

## Risks Or Blockers

- Live supplier replies and local marketplace captures can contain private information; keep them out of GitHub unless intentionally sanitized.
- LLM behavior depends on `OPENAI_API_KEY`; deterministic fallback exists but may be less complete.
- Mac browser collection may need platform-specific Chrome path handling if Workstream 01 Facebook collection is used there.
