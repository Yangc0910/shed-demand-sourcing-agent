# Workstream: Demand Listener / Local Market Signals

This file is the canonical workstream handoff for the active demand-monitoring lane.

See the fuller operational notes in:

- [demand-listener-ops-and-reporting.md](demand-listener-ops-and-reporting.md)

## Objective

Turn the local shed market monitor into a reliable private demand-listening workflow for compact resin/plastic sheds in Greater Boston.

## Scope

- Facebook Marketplace Boston collection
- Craigslist and watchlist ingestion
- local snippets
- LLM-assisted interpretation
- local demand scoring
- daily digest
- weekly report
- dashboard
- routine / scheduler reliability

## Current Status

- implemented and usable
- active recommendation remains `continue watching`
- Facebook login/session access works locally
- fresh automated Facebook capture still needs better bounded-runtime reliability

## Main Files

- [../shed_agent/facebook_marketplace.py](../shed_agent/facebook_marketplace.py)
- [../shed_agent/routine.py](../shed_agent/routine.py)
- [../shed_agent/llm_analysis.py](../shed_agent/llm_analysis.py)
- [../shed_agent/generate_dashboard.py](../shed_agent/generate_dashboard.py)
- [../config/shed_agent_config.json](../config/shed_agent_config.json)

## Next Steps

1. stabilize fresh Facebook capture within automation time limits
2. keep reducing noisy and non-local listing influence
3. verify a clean Mac continuation path
