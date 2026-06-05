# Tasks: Supplier RFQ & Communication Agent

## Completed

- Supplier data model.
- Product candidate data model.
- Supplier thread and message model.
- Human-approved message draft queue.
- Chinese and English RFQ template generator.
- Pasted supplier reply ingestion.
- LLM extraction with deterministic fallback.
- Missing-information detection.
- Follow-up question and draft generation.
- Deterministic confidence score.
- Risk checklist.
- Chinese Supplier RFQ Pack report.
- End-to-end scenario validation for strong, incomplete, and high-risk suppliers.
- Unit tests and scenario tests.
- GitHub/Codex handoff documentation.

## Pending

- Enter first real supplier manually.
- Run the full supplier workflow with real pasted replies.
- Review whether any real supplier fields need model additions.
- Verify Mac clone/setup/test path.

## Nice To Have

- Friendlier CLI helpers for selecting recent supplier/thread/draft IDs.
- Sanitized example dataset for demonstrations.
- Optional spreadsheet export for supplier comparison.
- Optional report copy into `docs/` when sanitized.

## Testing Tasks

- Keep running `py -m compileall shed_agent tests`.
- Keep running `py -m unittest discover -s tests`.
- Add tests whenever missing-info detection or scoring rules change.

## Deployment Tasks

- Keep as local CLI only.
- Use GitHub for code/documentation backup.
- Do not commit private runtime supplier JSON unless intentionally sanitized.
- Do not deploy a public UI.
