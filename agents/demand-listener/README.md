# Demand Listener Agent

Local decision-support agent for compact shed demand around Greater Boston.

## Role

- Collect and normalize local demand signals
- Score and verify candidates
- Generate digest/report/dashboard outputs
- Recommend the current market posture

## Main Entry Points

- `shed_agent/cli.py`
- `shed_agent/routine.py`
- `shed_agent/generate_daily_digest.py`
- `shed_agent/generate_dashboard.py`
- `shed_agent/decision.py`

## State

- `data/observations.json`
- `config/shed_agent_config.json`

## Current Status

Operational. Latest known recommendation from repository outputs: `continue watching`.
