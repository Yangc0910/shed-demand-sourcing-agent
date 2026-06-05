# Demand Listener Agent

Private local demand-monitoring workflow for compact resin/plastic sheds around Greater Boston.

## What It Does

- Adds manual observations and local snippets.
- Ingests configured demand sources.
- Imports local Facebook Marketplace captures.
- Scores and deduplicates observations.
- Generates daily digests, weekly reports, dashboards, and decision checks.

## What To Be Careful With

The user has asked not to modify Demand Listener collector logic unless absolutely necessary. Workstream 02 supplier work should not disturb this agent.

## Common Commands

```bash
shed-agent add-observation --text "4x6 resin shed, $450, Lexington"
shed-agent analyze-observations
shed-agent generate-daily-digest --out reports/daily-digest.md
shed-agent generate-dashboard --out reports/dashboard.html
shed-agent decision-check
```
