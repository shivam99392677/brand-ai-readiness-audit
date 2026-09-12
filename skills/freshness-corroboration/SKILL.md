---
name: freshness-corroboration
description: Checks timestamp metadata, update cadence, date consistency, staleness >12 months, and external corroboration via Wikidata, Wikipedia, and sameAs.
---

# Freshness & Corroboration Skill

## Purpose
Assesses content freshness indicators and external corroboration signals to ensure AI models recognize brand information as up-to-date and authoritatively supported.

## When to Use
Invoked by `audit-orchestrator` during recency and authority evaluation.

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`FC-01`** | **Date Inconsistency & Disagreement** | Medium | Flags conflicting dates between `dateModified`, `datePublished`, HTTP `Last-Modified`, and visible text. |
| **`FC-02`** | **Content Staleness (>12 Months)** | High / Medium | Detects core pages with newest content date older than 12 months with no update signals (ignoring footer copyright). |
| **`FC-03`** | **External Entity Corroboration** | High / Medium / Info | Corroborates brand entity against public knowledge sources (Wikidata, Wikipedia, official `sameAs` links). |

## Code Entrypoint
- Implementation module: [`src/analysis/freshness_corroboration.py`](../../src/analysis/freshness_corroboration.py)
- Unit tests: [`tests/test_analysis_skills.py`](../../tests/test_analysis_skills.py)
