# Supplier RFQ Tasks

## Completed Tasks

- Supplier, product, thread, and draft storage implemented
- RFQ template generation implemented
- Thread analysis and follow-up draft queue implemented
- Supplier RFQ report generation implemented
- Documentation and handoff structure added

## Pending Tasks

- Validate supplier workflow from a fresh clone
- Add more explicit schema migration guidance if data models change
- Review whether supplier data should stay in the same repository as demand state

## Nice-To-Have Tasks

- Add CSV export for supplier comparisons
- Add better landed-cost placeholders and comparison tables
- Add clearer audit history for manual send steps

## Testing Tasks

- Run supplier-related unit tests after clone on Mac
- Add tests for cross-platform path assumptions in supplier outputs

## Deployment Tasks

- Include supplier state JSONs in the first Git commit
- Keep repo private because supplier notes may be sensitive
