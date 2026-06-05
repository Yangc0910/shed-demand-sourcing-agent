# Demand Listener Agent Spec

## Agent Objective

Detect whether local compact shed demand is strong enough to justify moving from passive listening into supplier research or inventory planning.

## User Stories

- As an operator, I want a daily summary of meaningful local shed signals.
- As an operator, I want noisy marketplace results filtered so they do not distort decisions.
- As an operator, I want a simple recommendation such as `continue watching` or `start supplier RFQ`.
- As an operator, I want the workflow to survive across devices using GitHub-backed docs and state files.

## Inputs

- Manual observations and snippets
- Craigslist RSS URLs
- Watchlist URLs
- Optional Facebook Marketplace collection/import
- `config/shed_agent_config.json`
- Optional `OPENAI_API_KEY`

## Outputs

- Daily digest markdown
- Weekly report markdown
- Decision check markdown/text
- HTML dashboard
- Routine summary JSON/markdown

## Internal Workflow

1. Ingest or load observations
2. Extract structured fields
3. Score observations
4. Apply LLM verification or fallback verification
5. Deduplicate
6. Run decision logic
7. Generate reports/dashboard

## Data Files Used

- `data/observations.json`
- `data/llm_cache/`

## Safety / Approval Boundaries

- Does not bypass Facebook login or challenge flows
- Does not contact sellers
- Does not place orders or make purchases
- Should not be treated as a permit/zoning authority

## External Integrations

- Playwright
- Facebook Marketplace in a local interactive browser
- OpenAI Responses API

## Error Handling

- Missing API key falls back to deterministic verification
- Collector launch failure returns diagnostics instead of crashing the whole repo state
- Blocked fetches are recorded conservatively

## Future Improvements

- Mac-native routine helpers
- Better source coverage beyond Facebook/manual/Craigslist
- Stronger diffing of day-over-day signal changes
- Richer dashboard filtering and provenance links
