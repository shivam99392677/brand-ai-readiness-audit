---
name: Structured Data Audit
description: Validates Schema.org JSON-LD, Microdata, OpenGraph, and semantic HTML markup for AI entity extraction and machine readability.
---

# Structured Data Audit Skill

## Purpose
The **Structured Data Audit** skill evaluates the presence, syntax validity, coverage, and entity richness of structured metadata and semantic HTML on a brand's website. It ensures that AI search engines, knowledge graphs, and RAG pipelines can extract unambiguous entity definitions, product specifications, FAQ answers, and content relationships without hallucination.

---

## When to Use
Invoked by `audit-orchestrator` during the semantic extraction and machine readability evaluation phase.

---

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`SD-001`** | **JSON-LD Detection** | Info / Low | Detects presence of `<script type="application/ld+json">` blocks. |
| **`SD-002`** | **JSON-LD Parse Validity** | High | Verifies that all detected JSON-LD blocks parse as valid JSON syntax. |
| **`SD-003`** | **Schema Type Detection** | Info / Low | Extracts and lists all declared `@type` (or Microdata `itemtype`) schema values. |
| **`SD-004`** | **Entity Information Completeness** | Info / Medium | Checks completeness of core properties for `Organization`, `Person`, `Product`, `WebSite`, `FAQPage`, etc. |
| **`SD-005`** | **Structured Data vs Visible Content Consistency** | High | Deterministically verifies consistency between structured entity names and visible `<title>` / `<h1>` text. |
| **`SD-006`** | **Duplicate or Conflicting Structured Data** | Medium | Identifies multiple schema objects of the same type with conflicting canonical property values. |

---

## Implementation Principles
- **Observable Technical Facts:** Reports verified technical properties without speculating on unobservable search engine boosts.
- **Traceable Evidence:** Every finding includes precise evidence pointers (`location`, `source_url`, `evidence_type`, `observed`, `expected`).
- **Non-Critical Defaults for Missing Data:** Absence of optional structured data triggers `WARNING` or `INFO` findings rather than critical score caps.
- **Raw Payload Preservation:** Preserves raw JSON-LD schema dictionaries in evidence payloads while truncating excessively large blocks for memory efficiency.

---

## High-Level Responsibilities

1. **Schema.org JSON-LD & Microdata Extraction**:
   - Extracts all `<script type="application/ld+json">` payloads and embedded Microdata itemscopes from DOM snapshots.
   - Parses nested entity graphs and resolves `@id` references.

2. **Core Schema Type Validation**:
   - **`Organization` / `LocalBusiness`**: Verifies `name`, `legalName`, `url`, `logo`, `contactPoint`, and `sameAs` entity links.
   - **`WebSite`**: Checks `url`, `name`, and potential `potentialAction` (`SearchAction`) markup.
   - **`Product` / `SoftwareApplication`**: Checks `name`, `description`, `image`, `offers` (`price`, `priceCurrency`, `availability`), `aggregateRating`.
   - **`Article` / `BlogPosting`**: Checks `headline`, `author` (linked to `Person`), `datePublished`, `dateModified`, `publisher`.
   - **`FAQPage`**: Validates `mainEntity` array of `Question` and `Answer` objects.

3. **Syntax & Specification Compliance**:
   - Validates JSON-LD against official Schema.org vocabularies.
   - Detects syntax errors, missing mandatory properties, deprecated properties, and malformed URI strings.

4. **Entity Linkage & Social Graph**:
   - Evaluates `sameAs` links pointing to authoritative profiles (Wikidata, Wikipedia, LinkedIn, Twitter/X, Crunchbase, GitHub).
   - Audits OpenGraph (`og:title`, `og:description`, `og:image`, `og:url`) and Twitter Card metadata.

5. **Semantic HTML Document Hierarchy**:
   - Audits structural HTML5 landmark elements: `<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`, `<header>`, `<footer>`.
   - Audits structured presentation elements: `<table>`, `<thead>`, `<tbody>`, `<dl>`, `<dt>`, `<dd>`.

---

## Code Entrypoint
- Implementation module: [`src/analysis/structured_data_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/analysis/structured_data_audit.py)
- Unit tests: [`tests/test_structured_data_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/tests/test_structured_data_audit.py)

---

## Inputs
- **`rendered_dom_snapshots`** *(array of DOM documents, required)*: Fully rendered DOM snapshots from the Evidence Store.
- **`target_url`** *(string, required)*: Base domain of the audited website.

---

## Outputs
- **`machine_readability_score`** *(number, 0–100)*: Normalized sub-score.
- **`findings`** *(array of objects)*: Array of finding objects with `finding_id`, `category`, `severity`, `title`, `description`, `impact`, `evidence_ids`, and `remediation`.
- **`schema_inventory`**: JSON object mapping all discovered schema types, counts, and validation statuses.

---

## Evidence Expectations
- `EVID-SCHEMA-JSONLD`: Extracted raw JSON-LD code blocks.
- `EVID-SCHEMA-VALIDATION`: Validator error/warning logs and rule compliance tables.
- `EVID-OPENGRAPH`: Key-value pairs of extracted OpenGraph and social metadata.
- `EVID-SEMANTIC-HTML`: Element count and hierarchy tree of semantic HTML5 tags.

---

## False-Positive Considerations
- **Custom Schema Extensions**: Proprietary extension properties not in the base Schema.org vocabulary should be flagged as warnings, not syntax errors, if namespaced properly.
- **Multiple Organizations**: Multi-brand holdings or subsidiaries with multiple nested Organization schemas should not be penalized if parent-child relationships are declared via `parentOrganization` or `subOrganization`.
