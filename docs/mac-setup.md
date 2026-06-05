# Mac Setup

## Goal

Bring the repository up on macOS after cloning from GitHub without depending on Windows-local shell history or Codex thread history.

## Steps

```bash
git clone <repo-url>
cd shed-local-demand-sourcing-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m playwright install chromium
export OPENAI_API_KEY=...
python -m shed_agent.cli decision-check
python -m unittest discover -s tests
bash ./scripts/run_routine.sh
```

## Platform Notes

- Use `python3` to create the venv.
- Do not use the Windows PowerShell scripts from `scripts/`.
- Facebook login state does not sync from Windows; log in again locally if you plan to use Facebook collection.
- `config/shed_agent_config.json` may use a Windows `%LOCALAPPDATA%` browser-profile path. For Mac Facebook collection, change it locally to `.local/playwright/facebook-profile` or another Mac-local path.

## Recommended First Validation

```bash
python -m shed_agent.cli generate-dashboard
python -m shed_agent.cli generate-supplier-report
```
