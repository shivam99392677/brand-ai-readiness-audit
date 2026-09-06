---
name: Freshness & Corroboration
description: Audits timestamp metadata, content update cadence, stale core pages, and cross-source external corroboration while strictly adhering to missing-evidence protocols.
---

# Freshness & Corroboration Skill

## Purpose
The **Freshness & Corroboration** skill evaluates temporal metadata, content freshness signals, and external factual consistency across a brand's web presence. It ensures that AI search systems, RAG engines, and knowledge bases recognize brand information as timely, actively maintained, and authoritatively corroborated.

---

## When to Use
Invoked by `audit-orchestrator` during the recency, authority, and verification evaluation phase.

---

## High-Level Responsibilities

1. **Temporal Metadata Extraction & Audit**:
   - Inspects explicit machine-readable timestamps across all extracted pages:
     - Schema.org JSON-LD `datePublished` and `dateModified`.
     - HTTP response headers: `Last-Modified`, `ETag`, `Cache-Control`.
     - XML sitemap `<lastmod>` timestamps.
     - User-facing visual publication/update dates extracted from DOM.
   - Detects timestamp anomalies (e.g., `dateModified` in the future, `<lastmod>` missing or identical across entire sitemap).

2. **Stale Core Page Detection**:
   - Analyzes update cadences across core functional pages (Pricing, Product Specs, API Docs, Legal Terms).
   - Flags critical commercial pages that have not received documented updates or verification in >18 months, which risks LLM answer engines serving obsolete information.

3. **External Corroboration & Consistency**:
   - Evaluates observable external brand facts (where publicly accessible via search snippets or public registries).
   - Cross-checks core brand assertions (founding year, leadership, core product categories) against external knowledge sources.

4. **Strict Missing Evidence Protocol**:
   - **Critical Rule**: If external authority or third-party citation metrics cannot be reliably observed, this skill must explicitly report **`Unknown / Unavailable`** rather than fabricating numbers or scoring as `Failed`.
   - Redistributes scoring weights dynamically so unobservable external metrics do not unfairly depress the audit score.

---

## Inputs
- **`page_metadata_records`** *(array of objects, required)*: Headers, sitemap timestamps, and schema date properties from Evidence Store.
- **`derived_brand_context`** *(object, required)*: Internally derived brand profile.
- **`observable_external_records`** *(array of objects, optional)*: Public search snippets and external citations (if available).

---

## Outputs
- **`freshness_score`** *(number, 0–100)*: Normalized sub-score.
- **`findings`** *(array of objects)*:
  - `finding_id`: Unique identifier (e.g., `FIND-FRESH-001`).
  - `category`: `Freshness & Corroboration`.
  - `severity`: `Critical` (severe timestamp spoofing or obsolete pricing) | `High` | `Medium` | `Low`.
  - `title`: Short summary.
  - `description`: Detailed freshness or corroboration observation.
  - `impact`: Risk of AI engines serving stale or ungrounded responses.
  - `evidence_ids`: Referenced Evidence IDs (`EVID-SCHEMA-DATES`, `EVID-TIMESTAMP-HEADERS`, etc.).
  - `remediation`: Specific steps to update timestamps or sitemap configs.
- **`temporal_inventory`**: Per-page table of `datePublished`, `dateModified`, `Last-Modified`, and `<lastmod>` statuses.

---

## Evidence Expectations
- `EVID-TIMESTAMP-HEADERS`: HTTP response headers containing date and caching metadata.
- `EVID-SCHEMA-DATES`: Extracted JSON-LD date properties.
- `EVID-SITEMAP-LASTMOD`: Extracted `<lastmod>` tags from XML sitemap.
- `EVID-CORROBORATION-RECORDS`: Public search result snippets and knowledge base records.

---

## False-Positive Considerations
- **Evergreen Content**: Foundational company values, historical timeline pages, and core educational principles that do not change frequently must not be penalized as "stale" simply due to an older creation date.
- **Dynamic Footer Copyright Years**: JavaScript that automatically updates the copyright year in the footer must not be mistaken for substantive page content revisions.
- **Unavailability ≠ Failure**: Lack of external third-party backlink data or private domain authority metrics is treated as `Unknown`, never as a 0/100 failure.
