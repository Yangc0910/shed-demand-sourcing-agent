# ALL_MIGRATION_REPORTS

This file consolidates the GitHub migration reports for the major workstreams in this project.

Common repository baseline at the time of consolidation:

- Project name: `Shed Local Demand & Sourcing Agent`
- Git status: clean
- Current branch: `main`
- Latest local commit: `7eed67a Initial GitHub-ready project backup`
- Git remote: none configured yet
- Recommended private repo name: `shed-demand-sourcing-agent`

Common next commands after creating the GitHub repository:

```bash
git remote add origin https://github.com/YOUR_USERNAME/shed-demand-sourcing-agent.git
git remote -v
git push -u origin main
```

---

## Workstream 01 - Demand Listener / Local Market Signals

### Project

- `Shed Local Demand & Sourcing Agent`

### Workstream

- `Demand Listener / Local Market Signals`
- related operational handoff file:
  - [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md)

### Agent-related

- Yes

Primary agent:

- `Demand Listener`

### Main Purpose

Monitor local Greater Boston demand signals for compact resin/plastic sheds, separate real local demand from noise and retail benchmarks, and generate decision-oriented outputs such as digest, dashboard, and decision check.

### Files Changed For GitHub Migration

- [README.md](README.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [CODEX_HANDOFF.md](CODEX_HANDOFF.md)
- [.gitignore](.gitignore)
- [.gitattributes](.gitattributes)
- [docs/architecture.md](docs/architecture.md)
- [docs/mac-setup.md](docs/mac-setup.md)
- [docs/cross-device-sync.md](docs/cross-device-sync.md)
- [workstreams/demand-listener-ops-and-reporting.md](workstreams/demand-listener-ops-and-reporting.md)
- [workstreams/demand-listener-local-market-signals.md](workstreams/demand-listener-local-market-signals.md)
- [agents/demand-listener/README.md](agents/demand-listener/README.md)
- [agents/demand-listener/AGENT_SPEC.md](agents/demand-listener/AGENT_SPEC.md)
- [agents/demand-listener/TASKS.md](agents/demand-listener/TASKS.md)
- [config/shed_agent_config.json](config/shed_agent_config.json)
- [scripts/run_routine.sh](scripts/run_routine.sh)

### Git Status

- clean

### Repo Recommendation

- `shed-demand-sourcing-agent`

### Secrets Found

- no committed API keys or tokens found in tracked files
- local sensitive runtime material exists and is intentionally ignored:
  - `.local/playwright/facebook-profile`
  - `logs/`
  - `reports/`
  - `data/observations.json`
  - `data/llm_cache/`

### Mac Compatibility Issues

- Windows PowerShell helper scripts do not run on Mac
- Windows Task Scheduler setup does not carry over to Mac
- Facebook login/session must be re-established locally on the Mac
- `OPENAI_API_KEY` must be restored locally on the Mac
- the Python CLI is portable, but browser/session behavior remains machine-local

### Next Commands

```bash
git remote add origin https://github.com/YOUR_USERNAME/shed-demand-sourcing-agent.git
git remote -v
git push -u origin main
```

Recommended first Mac validation after clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m playwright install chromium
python -m unittest discover -s tests
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-dashboard
```

### Current Implementation Status

- operational and actively used
- digest, decision check, dashboard, and routine flow are implemented
- Facebook collection works through local-session paths with some runtime fragility
- current business recommendation remains `continue watching`

---

## Workstream 02 - Supplier RFQ / China Sourcing

### Project

- `Shed Local Demand & Sourcing Agent`

### Workstream

- `Supplier RFQ / China Sourcing`

This workstream is represented in the repository primarily through the supplier agent docs and supplier modules:

- [agents/supplier-rfq/README.md](agents/supplier-rfq/README.md)
- [agents/supplier-rfq/AGENT_SPEC.md](agents/supplier-rfq/AGENT_SPEC.md)
- [agents/supplier-rfq/TASKS.md](agents/supplier-rfq/TASKS.md)
- [shed_agent/supplier/](shed_agent/supplier)

### Agent-related

- Yes

Primary agent:

- `Supplier RFQ Agent`

### Main Purpose

Support cautious supplier evaluation, quote parsing, follow-up drafting, and sourcing readiness tracking without automating outbound messaging or purchase commitments.

### Files Changed For GitHub Migration

- [README.md](README.md)
- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [CODEX_HANDOFF.md](CODEX_HANDOFF.md)
- [.gitignore](.gitignore)
- [.gitattributes](.gitattributes)
- [docs/architecture.md](docs/architecture.md)
- [docs/mac-setup.md](docs/mac-setup.md)
- [docs/cross-device-sync.md](docs/cross-device-sync.md)
- [agents/supplier-rfq/README.md](agents/supplier-rfq/README.md)
- [agents/supplier-rfq/AGENT_SPEC.md](agents/supplier-rfq/AGENT_SPEC.md)
- [agents/supplier-rfq/TASKS.md](agents/supplier-rfq/TASKS.md)

### Git Status

- clean

### Repo Recommendation

- `shed-demand-sourcing-agent`

Alternative if this workflow is ever split into its own repo:

- `supplier-rfq-agent`

### Secrets Found

- no committed supplier credentials, tokens, or API keys found in tracked files
- local/private supplier runtime files are intentionally ignored:
  - `data/suppliers.json`
  - `data/product_candidates.json`
  - `data/supplier_threads.json`
  - `data/supplier_message_queue.json`
  - `data/supplier_llm_cache/`

### Mac Compatibility Issues

- supplier CLI logic is portable Python
- Windows-specific wrapper scripts are not portable
- `OPENAI_API_KEY` must be restored locally for LLM-assisted extraction/drafting
- no Mac-native scheduler path is documented yet for supplier automation

### Next Commands

```bash
git remote add origin https://github.com/YOUR_USERNAME/shed-demand-sourcing-agent.git
git remote -v
git push -u origin main
```

Recommended first Mac validation after clone:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests
python -m shed_agent.cli generate-supplier-report
```

### Current Implementation Status

- implemented in code and tested
- designed as human-approved workflow only
- suitable for private continuation after clone
- not the currently active operational lane in this thread

---

## Notes

- The repository currently keeps code and documentation in Git, while runtime state remains local and ignored by default.
- If cross-device syncing of observations or supplier state becomes necessary later, that should be handled by an explicit export/import policy instead of silently committing all runtime JSON files.
