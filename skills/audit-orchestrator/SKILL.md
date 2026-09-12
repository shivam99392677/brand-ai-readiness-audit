---
name: audit-orchestrator
description: Master entrypoint skill orchestrating end-to-end brand AI readiness audits across all 6 specialized analysis skills.
---

# Audit Orchestrator Skill

## Purpose
The **Audit Orchestrator** is the primary marketplace entrypoint skill for the Brand AI Readiness Audit package. It validates the target URL, conducts site-wide discovery and crawling, executes the canonical evidence extraction layer, coordinates the execution of all 6 registered audit sub-skills, merges findings, enforces error isolation, and synthesizes the canonical Adobe Report JSON.

## When to Use
Invoked as the primary CLI, API, or marketplace entrypoint when initiating a comprehensive AI readiness audit for a web domain.

## Execution Workflow
1. **Target Validation & Bounded Crawl:** Validates that the provided target URL has a valid scheme and hostname, and discovers pages within configurable depth/page limits.
2. **Canonical Evidence Extraction:** Coordinates modular extractors to produce a normalized, traceable `ExtractionResult` with sequential `EV-00001` IDs.
3. **Sub-Skill Delegation:** Dispatches the full evidence store to all 6 registered analysis skills:
   - `crawl-render-audit`: Evaluates HTTP headers, robots directives, DOM text extractability, and SSR/CSR parity.
   - `structured-data-audit`: Audits Schema.org JSON-LD syntax, entity types, completeness on product pages, and visible content consistency.
   - `fact-quality-audit`: Detects cross-page contradictions (pricing, hours, refunds), unitless numbers, and ungrounded superlatives.
   - `freshness-corroboration`: Evaluates timestamp consistency, content staleness >12 months (ignoring copyright), and public source corroboration (Wikidata, Wikipedia, sameAs).
   - `entity-identity-audit`: Audits brand entity naming consistency between title/H1 and schema, sameAs links (404 detection), and cross-page NAP consistency.
   - `engagement-audit`: Evaluates above-the-fold orientation (Who/What/Next), navigation coverage of offerings, interior breadcrumb hierarchy, and actionable CTAs.
4. **Error Isolation:** Encapsulates sub-skill exceptions, guaranteeing the audit finishes and returns valid findings.
5. **Adobe Report Synthesis:** Uses `AdobeReportComposer` to filter out non-defects, sort by severity, and output canonical Adobe `report.json`.

## Code Entrypoint
- Implementation module: [`src/orchestrator.py`](../../src/orchestrator.py)
- CLI Usage: `python -m src.orchestrator https://example.com -o report.json`
- Unit tests: [`tests/test_orchestrator.py`](../../tests/test_orchestrator.py)
