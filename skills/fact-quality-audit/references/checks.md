# Fact Quality Audit - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| FQ-02 | Contradictory Proposition Claims | High | Identifies conflicting pricing, refund policy windows, operating hours, or founding years across pages |
| FQ-03 | Unitless Numeric Metrics | Medium | Identifies numerical metrics lacking explicit units, benchmarks, or baseline comparators |
| FQ-04 | Ungrounded Superlatives | Medium | Flags marketing superlatives (#1, best, only, leading) lacking adjacent supporting citations |

## Guardrails
- Cross-page contradictions must name both URLs and both values.
- Superlatives only flagged when adjacent supporting citations are absent.
