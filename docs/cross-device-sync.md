# Cross-Device Sync

## Goal

Use GitHub as the durable source of truth for:

- code
- documentation
- project status
- workstream status
- next actions
- agent instructions

## What Git Tracks

- source code
- tests
- config templates and tracked config files
- README / handoff / workstream / agent docs
- helper scripts

## What Git Does Not Track

- browser profiles
- Playwright caches
- logs
- generated reports
- runtime observation state
- local LLM caches
- local supplier runtime state

These are intentionally gitignored so the repo stays portable and credential-safe.

## Windows And Mac Expectations

- Windows uses PowerShell helper scripts in `scripts/*.ps1`
- Mac should use `python3 -m ...` and [scripts/run_routine.sh](../scripts/run_routine.sh)
- each machine must configure its own `OPENAI_API_KEY`
- each machine must establish its own Facebook login/session locally

## Recommended Mac Validation After Clone

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m playwright install chromium
python -m unittest discover -s tests
python -m shed_agent.cli decision-check
python -m shed_agent.cli generate-dashboard
```
