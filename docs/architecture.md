# Architecture

## Overview

The repository has one Python package, `shed_agent`, with two operational domains:

- Demand Listener domain
- Supplier RFQ domain

Both are exposed through a single CLI.

## Demand Listener Flow

```text
Sources
  -> manual observations / local snippets / Craigslist RSS / watchlist URLs / Facebook capture
Extraction
  -> shed_agent.extract_listing
Scoring
  -> shed_agent.score_observation
Verification
  -> shed_agent.llm_analysis or fallback verification
Decision
  -> shed_agent.decision
Outputs
  -> daily digest / weekly report / dashboard / routine summary
State
  -> data/observations.json
```

## Supplier RFQ Flow

```text
Supplier + product setup
  -> suppliers.json / product_candidates.json
Conversation tracking
  -> supplier_threads.json
Draft queue
  -> supplier_message_queue.json
Analysis
  -> supplier.llm_extract / supplier.conversation / supplier.scoring
Outputs
  -> supplier RFQ pack / pending drafts / follow-up plans
```

## Scheduling

- Automated routine entry point: `shed_agent.routine.run_routine`
- Windows wrapper: `scripts/run_routine.ps1`
- Generated runtime artifacts: `logs/` and `reports/`

## Cross-Device Model

- Git tracks code, docs, config, tests, and helper scripts.
- Git ignores local runtime JSON state, generated outputs, browser profiles, and LLM caches by default.
- Each machine must restore its own environment variables and Facebook login session.
