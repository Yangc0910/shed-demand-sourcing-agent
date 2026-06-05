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
- The checked-in config now uses a repo-local `.local/playwright/facebook-profile` path so the browser profile can be recreated safely on Mac.

## Recommended First Validation

```bash
python -m shed_agent.cli generate-dashboard
python -m shed_agent.cli generate-supplier-report
```
