---
name: structured-data-audit
description: Validates Schema.org JSON-LD syntax, entity types, completeness on product pages, and visible content consistency.
---

# Structured Data Audit Skill

## Purpose
Inspects web page HTML to audit structured data markup (JSON-LD script blocks, Microdata, and relevant meta tags) and reports observable technical findings without treating general missing schema as defects.

## When to Use
Invoked by `audit-orchestrator` during the semantic structured data analysis phase.

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`SD-001`** | **JSON-LD Detection** | Info / Low | Detects presence of `<script type="application/ld+json">` blocks. |
| **`SD-002`** | **JSON-LD Parse Validity** | High | Verifies that all detected JSON-LD blocks parse as valid JSON syntax. |
| **`SD-003`** | **Schema Type Detection** | Info | Extracts and lists declared `@type` schema values across the site. |
| **`SD-004`** | **Entity Information Completeness** | High / Medium / Info | Checks completeness of core properties for `Product`, `Offer`, `Organization`, etc. on applicable pages. |
| **`SD-005`** | **Structured Data vs Visible Content Consistency** | High | Deterministically verifies consistency between structured entity names and visible `<title>` / `<h1>` text. |
| **`SD-006`** | **Duplicate or Conflicting Structured Data** | Medium | Identifies multiple schema objects of the same type with conflicting canonical property values. |

## Implementation Principles
- **Defects on Real Issues Only:** Only flags syntax errors or incomplete Product/Offer schemas on pages that are classified as product pages. Missing schema on general pages is informational.
- **Traceable Evidence:** Every finding includes precise evidence pointers (`location`, `source_url`, `evidence_type`, `observed`, `expected`).

## Code Entrypoint
- Implementation module: [`src/analysis/structured_data_audit.py`](../../src/analysis/structured_data_audit.py)
- Unit tests: [`tests/test_structured_data_audit.py`](../../tests/test_structured_data_audit.py)
