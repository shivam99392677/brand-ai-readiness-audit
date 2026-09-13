# `src/shared/` — Canonical Evidence Schema

**Business logic:** the honesty contract. Every sentence in `findings[].evidence` is only as trustworthy as the structure defined here: an evidence item must say *what type of fact it is*, *where it came from* (URL + location pointer), and *what exactly was observed*. The schema deliberately contains no findings and no scores — the split between "data" (here) and "judgment" (`src/analysis/`) is what lets a human re-verify any claim.

**Tech logic:** `EvidenceType` enum classifies every fact the system can capture (HTTP, raw artifacts, metadata, text blocks, schema, robots, freshness, entity, links, media, coverage, absence). `Provenance` is the traceability pointer (source, url, location, selector, path, line, context) with a validator that keeps `url` and `source_url` in sync. `CanonicalEvidence` is the Pydantic record all extractors emit; `ExtractionResult` is the container the skills consume. Property aliases (`source_url`, `observed`, `location`) keep audit findings compatible.

```mermaid
flowchart TD
    E["EvidenceType enum<br/>http_status, raw_html, page_metadata, heading, paragraph,<br/>jsonld_raw/parsed, robots_rule, freshness_date, entity_name/phone/address,<br/>same_as_link, link_item, image_item, form_item, crawl_coverage, extraction_absence"] --> C["CanonicalEvidence"]
    P["Provenance{source, source_url, location, selector, path, line_number, context}"] --> C
    C --> AL["compat aliases:<br/>source_url / observed / location"]
    C --> ID["id: EV-00001 (EvidenceIdGenerator)"]
    ID --> RES["ExtractionResult{evidence[], errors[], metadata}"]
    RES --> SKILLS["audit skills consume — never the raw HTML"]
```

### `evidence_schema.py`
**Business:** the single vocabulary of the audit. Skills and extractors share it, so a finding's evidence is always structurally re-verifiable, and an evaluator can diff one run against another.
**Tech:** `CanonicalEvidence` (id, type, source, url, timestamp, data, provenance, is_raw/raw_ref) + `ExtractionError` (extractor, source, error, details) + `ExtractionResult`. The `Provenance` model validator normalizes `url` ↔ `source_url` so either field can be used.

```mermaid
flowchart LR
    X["extractor emits"] --> V{"Pydantic validation:<br/>type known? provenance complete?"}
    V -->|"ok"| C["CanonicalEvidence"]
    V -->|"no"| ERROR["error recorded, audit continues"]
    C --> RAW{"raw artifact?"}
    RAW -->|"yes"| RF["is_raw + raw_ref -> externally stored payload"]
    RAW -->|"no"| DATA["data: normalized factual dict"]
    DATA --> OUT["ExtractionResult"]
```

**Parent:** [src README](../README.md).