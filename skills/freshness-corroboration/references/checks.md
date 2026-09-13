# Freshness & Corroboration - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| FC-01 | Date Inconsistency & Disagreement | Medium | Flags conflicting dates between dateModified, datePublished, HTTP Last-Modified, and visible text |
| FC-02 | Content Staleness (>12 Months) | High / Medium | Detects core pages with newest content date older than 12 months with no update signals (ignoring footer copyright) |
| FC-03 | External Entity Corroboration | High / Medium / Info | Corroborates brand entity against public knowledge sources (Wikidata, Wikipedia, sameAs links) |

## Guardrails
- Footer copyright years ignored; only machine-readable timestamps parsed.
- Public knowledge graph queries fail gracefully without blocking the audit.
- Max 3 external GET requests per site (FC-03 cap).
