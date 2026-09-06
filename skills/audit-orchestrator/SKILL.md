---
name: Audit Orchestrator
description: Master orchestrator and sole entrypoint skill for coordinating end-to-end Brand AI Readiness Audits across Off-site Discoverability and On-site Engagement using URL-only input.
---

# Audit Orchestrator Skill

## Purpose
The **Audit Orchestrator** is the master entrypoint skill for the Brand AI Readiness Audit package. It validates the target URL, derives all necessary brand context automatically, initializes the immutable Evidence Store, coordinates execution across registered specialized audit sub-skills, validates evidence grounding, and synthesizes normalized scores and actionable remediation reports.

---

## Input Constraint & Automated Context Derivation
The orchestrator operates under a strict **URL-only input constraint**. It does **NOT** require or accept user-provided `brand_domain_context`, `canonical_brand_profile`, keyword lists, or private analytics credentials.

All brand context is derived internally via the **Automated Context Discovery Engine**:
1. Crawls homepage, `/about`, `/contact`, `/pricing`, and sitemap.
2. Extracts brand name, legal entity, official logos, core product/service offerings, and value propositions.
3. Automatically synthesizes candidate branded queries (*"What does [Brand] do?"*, *"What is [Brand]'s pricing model?"*) and categorical discovery queries (*"What are the best [Category] tools for [Target Audience]?"*).

---

## High-Level Responsibilities

```
                                [ target_url ]
                                      │
                                      ▼
                        1. Automated Context Discovery
                                      │
                                      ▼
                        2. Crawl & Render Engine
                                      │
                                      ▼
                        3. Immutable Evidence Store
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
Dimension A: Off-site Discoverability                     Dimension B: On-site Engagement
├── crawl-render-audit                                    └── engagement-audit
├── structured-data-audit                                     ├── First-Visit Clarity
├── fact-quality-audit                                        ├── Content Scannability
├── freshness-corroboration                                   ├── Navigation & Findability
└── entity-identity-audit                                     ├── CTA & User Journey
                                                              ├── Performance & Stability
                                                              ├── Mobile UX
                                                              ├── Trust & Credibility
                                                              ├── Observable Accessibility
                                                              └── AI-Agent Readiness
         │                                                         │
         └────────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
                        4. Evidence Validation Engine
                                      │
                        5. Normalized Scoring & Penalty Caps
                                      │
                                      ▼
                        6. Actionable Recommendations
                                      │
                                      ▼
                        7. Final Audit Deliverables
```

1. **Pipeline Initialization & Context Derivation**: Validates that the provided target URL contains a valid HTTP/HTTPS scheme and domain host, discovers core brand pages, and constructs internal brand context.
2. **Crawl & Render Execution**: Triggers `SiteCrawler` and `Playwright` to capture raw HTML, hydrated post-JS DOM, HTTP headers, and Core Web Vitals.
3. **Evidence Store Ingestion**: Persists structured evidence (`WebsiteEvidence`, `PageEvidence`) with unique deterministic Evidence IDs (`EVID-DOM-RAW`, `EVID-SCHEMA-JSONLD`, etc.).
4. **Sub-Skill Dispatch & Error Isolation**: Coordinates execution across registered specialized audit skills with robust exception encapsulation so individual sub-skill failures do not crash the pipeline:
   - `crawl-render-audit`: Technical SEO, AI crawler `robots.txt`, SSR vs CSR DOM delta, sitemaps.
   - `structured-data-audit`: Schema.org JSON-LD, Microdata, OpenGraph, semantic HTML.
   - `fact-quality-audit`: Proposition extraction, claim ambiguity, cross-page contradictions, hallucination vulnerability.
   - `freshness-corroboration`: Temporal metadata (`dateModified`, `<lastmod>`), update cadence, external corroboration.
   - `entity-identity-audit`: Internally derived canonical entity model, cross-page NAP consistency, `sameAs` links.
   - `engagement-audit`: Comprehensive 9-pillar On-site Engagement evaluation.
5. **Observed AI Visibility Testing**: Dispatches derived queries to AI search engines, recording query + raw response + citations + prominence + accuracy into the Evidence Store.
6. **Evidence Validation**: Enforces that 100% of reported findings cite verifiable Evidence IDs.
7. **Scoring & Synthesis**: Computes normalized 0–100 sub-scores and overall readiness index using calibrated weights.
8. **Report Generation**: Emits unified `AuditReport` JSON structure and executive markdown report.

---

## Code Entrypoints
- Implementation module: [`src/orchestrator.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/orchestrator.py)
- Evidence models: [`src/evidence/models.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/evidence/models.py)
- Unit tests: [`tests/test_orchestrator.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/tests/test_orchestrator.py)

---

## Inputs
- **`target_url`** *(string, required)*: Primary brand domain or URL to audit (e.g., `https://example.com`).
- **`config_path`** *(string, optional)*: Path to custom `audit-config.yaml`.

---

## Outputs
- **`audit_report.json`**: Structured audit results, evidence mappings, category sub-scores, and overall AI readiness index.
- **`executive_summary.md`**: Markdown summary containing key findings and prioritized remediation steps.

---

## Scoring Model & Hierarchy

$$\text{Overall Score} = (0.50 \times \text{Off-site Discoverability}) + (0.50 \times \text{On-site Engagement})$$
