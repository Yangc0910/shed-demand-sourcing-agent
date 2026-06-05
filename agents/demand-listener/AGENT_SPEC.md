# Agent Spec: Demand Listener Agent

## Objective

Collect and analyze local demand evidence for compact resin/plastic sheds so the user can decide whether to source a small inventory batch.

## User Stories

- As the user, I can paste a local listing or post and have it scored.
- As the user, I can import or collect configured marketplace signals.
- As the user, I can generate a digest or dashboard to understand market demand.
- As the user, I can run a decision check before moving into supplier RFQ work.

## Inputs

- Manual listing text.
- Local snippets from community sources.
- Craigslist RSS URLs.
- Watchlist URLs.
- Retail comparable URLs.
- Local Facebook Marketplace capture JSON.
- Configuration in `config/shed_agent_config.json`.

## Outputs

- Scored observations.
- Deduplicated observation store.
- Daily digest.
- Weekly market report.
- Local HTML dashboard.
- Decision-check recommendation.

## Internal Workflow

1. Collect or enter observations.
2. Extract listing facts.
3. Score relevance, buyer intent, delivery gap, and target fit.
4. Deduplicate repeated signals.
5. Optionally run LLM-assisted analysis.
6. Generate reports and decision checks.

## Data Files Used

- `data/observations.json`
- `data/facebook-chrome-capture-*.json`
- `data/llm_cache/`
- `logs/`
- `reports/`

These are runtime/private files and should stay out of Git.

## Safety And Approval Boundaries

- Private local workflow.
- Browser/session data remains local.
- No automatic supplier outreach.
- No order or payment behavior.

## External Integrations

- Optional Playwright/Chrome for local Facebook Marketplace collection.
- Optional OpenAI API for listing analysis when `OPENAI_API_KEY` is available.
- Craigslist RSS and configured URLs when enabled.

## Error Handling

- LLM analysis falls back or records unavailable status when no API key exists.
- Facebook collection records challenge/login/session issues in summaries.
- Routine run can skip collectors based on config.

## Future Improvements

- More Mac-specific setup documentation for Facebook collection.
- More robust source health checks.
- Optional sanitized sample observations for GitHub demos.
