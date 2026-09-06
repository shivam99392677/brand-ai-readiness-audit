# System Architecture Documentation

## Overview

The **Brand AI Readiness Audit** system is an evidence-first, automated evaluation platform designed to assess a brand's digital presence across two foundational dimensions:
1. **Off-site Discoverability** (How effectively search engines and generative AI systems crawl, index, understand, retrieve, surface, and cite the brand).
2. **On-site Engagement** (How effectively the website helps human visitors and AI agents understand offerings, navigate, trust, and convert).

The system operates strictly on a **URL-only input constraint**: users provide only a target website URL. All brand context, offerings, canonical entity models, and representative discovery queries are derived automatically from the website's structure, content, and observable external signals.

---

## High-Level Architecture Pipeline

```
                                 [ Target Website URL ]
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              1. Automated Context Discovery           │
               │   (Extract Brand Name, Entity Profile, Core Products, │
               │     Value Props, and Discovery Query Candidates)      │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              2. Crawl & Rendering Engine              │
               │   (Fetch Raw HTML, Execute Headless JS Rendering,     │
               │     Capture HTTP Headers, Sitemaps, and robots.txt)   │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              3. Immutable Evidence Store              │
               │  (Raw DOM, Rendered DOM, Schema JSON-LD, Text Blocks, │
               │   Header Dumps, Screenshot Viewports, Query Records)  │
               └───────────────────────────┬───────────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
┌─────────────────────────────────────────┐ ┌─────────────────────────────────────────┐
│     Dimension A: Off-site Discovery     │ │      Dimension B: On-site Engagement    │
│  ├── A.1 On-Page SEO & Content Quality  │ │  ├── B.1 First-Visit Clarity            │
│  ├── A.2 Technical SEO & Crawlability   │ │  ├── B.2 Content Engagement             │
│  ├── A.3 Off-Page Authority (Observable)│ │  ├── B.3 Navigation & Findability       │
│  ├── A.4 AI / GEO Discoverability       │ │  ├── B.4 CTA & User Journey             │
│  │   ├── Structural AI Readiness        │ │  ├── B.5 Performance & Stability        │
│  │   └── Observed AI Visibility Testing │ │  ├── B.6 Mobile UX & Responsiveness     │
│  ├── A.5 Machine Readability & Entity   │ │  ├── B.7 Trust, Credibility & Compliance│
│  └── A.6 Freshness & Corroboration      │ │  ├── B.8 Observable Accessibility       │
│                                         │ │  └── B.9 AI-Agent Interaction Readiness │
└─────────────────────────────────────────┘ └─────────────────────────────────────────┘
                     │                                           │
                     └─────────────────────┬─────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              4. Evidence Validation Engine            │
               │   (Enforce Fact Grounding & Reject Un-anchored Claims)│
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │             5. Audit-Derived Scoring Engine           │
               │   (Compute Normalized 0–100 Scores & Penalty Caps)    │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │            6. Actionable Remediation Engine           │
               │     (Map Finding ➔ Evidence ➔ Impact ➔ Specific Fix)  │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │               7. Final Audit Deliverables             │
               │     (Structured JSON Artifact & Executive Report)     │
               └───────────────────────────────────────────────────────┘
```

---

## Architectural Component Separation

To prevent model hallucination and ensure reproducible audits, the architecture strictly segregates responsibilities across clear decoupled layers:

### 1. Discovery & Site Crawler (`src/crawler/`)
- **Responsibility:** Discover reachable pages, extract crawler rules, and fetch page HTML.
- **Components:**
  - `RobotsTxtParser` ([`src/crawler/robots.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/crawler/robots.py)): Parses user-agent specific rules (`*`, `GPTBot`, `ClaudeBot`, `PerplexityBot`) and sitemap locations.
  - `SitemapParser` ([`src/crawler/sitemap.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/crawler/sitemap.py)): Extracts child sitemaps and target URLs from sitemap indices and urlsets.
  - `PageRoleClassifier` ([`src/crawler/role_classifier.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/crawler/role_classifier.py)): Categorizes URLs into functional roles (`homepage`, `about`, `contact`, `product`, `terms`, `documentation`).
  - `SiteCrawler` ([`src/crawler/engine.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/crawler/engine.py)): Executes depth-bounded crawl using custom or default HTTP fetchers.

### 2. General Evidence Extraction (`src/extraction/`)
- **Responsibility:** Extract sitewide and per-page DOM evidence without domain-specific audit assumptions.
- **Extractors:**
  - `extract_page_metadata` ([`src/extraction/metadata.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/extraction/metadata.py)): Extracts page titles, meta descriptions, canonical URLs, OG tags, and language declarations.
  - `extract_page_content` ([`src/extraction/page.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/extraction/page.py)): Parses visible headings, paragraph blocks, lists, tables, blockquotes, dates, and contact signals.
  - `extract_page_images` ([`src/extraction/images.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/extraction/images.py)): Filters tracking pixels and favicons while preserving figure captions and image dimensions.
  - `extract_page_links_and_resources` ([`src/extraction/links.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/extraction/links.py)): Extracts internal/external links, downloadable document resources (PDF, CSV), and interactive forms.
  - `extract_structured_data` ([`src/extraction/structured_data.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/extraction/structured_data.py)): Extracts JSON-LD scripts, OpenGraph, Microdata, and validates JSON-LD syntax.

### 3. Shared Evidence Store (`src/evidence/models.py`)
- **Responsibility:** Persist immutable, structured evidence models for the entire audited domain.
- **Key Models:**
  - `WebsiteEvidence`: Container for all `PageEvidence`, `RobotsEvidence`, and `SitemapEvidence`.
  - `PageEvidence`: Structured page snapshot containing metadata, headings, images, links, forms, documents, dates, and contacts.
  - `Provenance`: Standardized tracking of evidence source URL and DOM location context.

### 4. Semantic Understanding & Context Synthesis (`src/analysis/understanding.py`)
- **Responsibility:** Automatically infer canonical entity profiles and provide an extensible interface (`SemanticUnderstandingAdapter`) for AI discovery query generation and factual reasoning.
- **Operations:**
  - Baseline `BaselineUnderstandingAdapter` provides deterministic fallbacks.
  - Pluggable adapter interface accepts `WebsiteEvidence` and returns enriched semantic insights.

### 5. Specialized Audit Skills (`src/analysis/`)
- **Responsibility:** Perform domain audits on top of `WebsiteEvidence` across both Off-site Discoverability and On-site Engagement dimensions.
- **Skills:**
  - `crawl_render_audit` ([`src/analysis/crawl_render_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/analysis/crawl_render_audit.py)): Evaluates site crawlability, HTTP status, meta tags, heading hierarchy, content depth, and site coverage.
  - `structured_data_audit` ([`src/analysis/structured_data_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/analysis/structured_data_audit.py)): Evaluates JSON-LD presence, parse validity, schema types, entity completeness, and visible content consistency.
  - Additional sub-skills for fact quality, freshness, entity consistency, and on-site engagement.

### 6. Scoring Engine & Master Orchestrator (`src/orchestrator.py`)
- **Responsibility:** Coordinate end-to-end execution, aggregate audit findings across all skills into a unified `AuditReport`, and compute normalized 0–100 readiness scores with severity penalty caps.
