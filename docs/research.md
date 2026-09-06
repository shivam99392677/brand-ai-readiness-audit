# Research Log & Domain Knowledge Base

This document establishes the empirical foundations, literature review, technical standards, tool evaluations, and algorithmic methodologies powering the **Brand AI Readiness Audit** system.

---

## 1. AI Search & Generative Engine Optimization (GEO / AEO)

### 1.1 The Shift from Traditional Search to Generative Discovery
Traditional search engines (Google, Bing) rely on inverted indexes, PageRank, and lexical/dense retrieval to rank 10 blue links. In contrast, modern AI-driven answer engines (ChatGPT Search, Perplexity AI, Google AI Overviews, Microsoft Copilot, Claude with Search) synthesize direct natural language answers from multi-document retrieval-augmented generation (RAG) pipelines.

### 1.2 Key Mechanics of AI Discovery & Citation Triggers
Empirical research into Generative Engine Optimization (GEO) indicates that LLMs prioritize sources based on:
1. **Direct Answer Density**: Content blocks that answer high-intent questions concisely within the first 1–2 sentences of a section.
2. **Information Extraction Ease**: Structured lists (`<ul>`, `<ol>`), markdown tables, and definition lists (`<dl>`) that can be tokenized cleanly without complex parsing.
3. **Entity Disambiguation & Authority**: Unambiguous brand entity declarations linked via Schema.org `sameAs` to trusted knowledge graphs (Wikidata, Wikipedia, LinkedIn).
4. **Factual Corroboration**: Cross-domain consistency of key propositions (e.g., pricing, features, founding dates) across independent web publications.
5. **Freshness Signaling**: Explicit temporal metadata (`dateModified`, HTTP `Last-Modified`) indicating active maintenance.

### 1.3 Empirical AI Visibility Testing Methodology
Rather than relying purely on static crawler checks, true AI readiness requires empirical verification:
- **Branded Query Evaluation**: Testing direct queries (*"What does [Brand] do?", "What is [Brand]'s pricing model?"*) to measure brand recall, prominence, and factual accuracy.
- **Categorical Discovery Query Evaluation**: Testing non-branded high-intent category queries (*"What are the best [Category] solutions for [Target Segment]?"*) to measure category presence and source citation rates.
- **Evidence Tuple Preservation**: Every test captures `{ query, ai_system, raw_response, brand_mentioned, domain_cited, prominence_rank, factual_accuracy_score, evidence_ids }`.

---

## 2. Crawler Mechanics & JavaScript Rendering Behavior

### 2.1 AI User-Agent Crawlers vs. Search Engine Bots
Different AI organizations deploy specialized crawlers with distinct capabilities, rendering limits, and `robots.txt` compliance rules:

| Crawler User-Agent | Organization | Purpose | JavaScript Rendering Support |
| :--- | :--- | :--- | :--- |
| **`GPTBot`** | OpenAI | Training data collection & indexation | Limited / Text-first |
| **`OAI-SearchBot`** | OpenAI | Real-time ChatGPT Search retrieval | Pre-render / Headless |
| **`ClaudeBot`** | Anthropic | Training & AI retrieval | Text-first / Fast fetch |
| **`PerplexityBot`** | Perplexity AI | Real-time search index & answer grounding | Partial Headless Browser |
| **`Google-Extended`** | Google | Control token for Gemini training data | N/A (Directive token) |
| **`Googlebot`** | Google | Web indexing (supports full WRS rendering) | Full Chrome Headless |
| **`Bytespider`** | ByteDance | Training & search indexation | High-frequency / Fast fetch |
| **`Amazonbot`** | Amazon | Alexa & Bedrock search/indexing | Text-first |

### 2.2 Client-Side Rendering (CSR) vs. Server-Side Rendering (SSR)
A major risk for modern JavaScript-heavy web applications (built with React, Next.js, Vue, Angular, Svelte) is that while standard search bots like Googlebot eventually execute JavaScript via the Web Rendering Service (WRS), many AI retrieval scrapers only fetch raw HTML via lightweight HTTP clients (`curl`/`httpx`). If essential product information, pricing, or metadata is populated purely via client-side hydration, AI engines perceive the page as empty or thin content.

The audit measures the **DOM Delta**:
$$\text{DOM Delta} = \frac{|\text{Tokens}(\text{Rendered DOM}) - \text{Tokens}(\text{Raw HTML})|}{\text{Tokens}(\text{Rendered DOM})}$$
A high DOM Delta (>40%) on core informational text indicates severe CSR vulnerability.

---

## 3. Structured Data & Schema.org Specifications

### 3.1 Essential Schemas for Entity Disambiguation
JSON-LD embedded within `<script type="application/ld+json">` is the gold standard for communicating unambiguous entity knowledge to LLM parsers:
- **`Organization`**: Declares legal name, brand aliases, official logo, founding date, headquarters, contact points, and `sameAs` social profile array.
- **`WebSite`**: Declares search action endpoints (`SearchAction`) and canonical domain URI.
- **`Product` / `SoftwareApplication`**: Declares pricing, currencies, feature lists, operating systems, and user ratings.
- **`Article` / `BlogPosting`**: Declares `headline`, `author` (linked to `Person` schema), `datePublished`, `dateModified`, and `publisher`.
- **`FAQPage`**: Provides explicit Question-Answer pairs that LLM retrieval pipelines extract directly into conversational answers.
- **`LocalBusiness`**: Declares exact physical NAP (Name, Address, Phone), geo-coordinates, and operating hours.

### 3.2 Semantic HTML Elements
Beyond JSON-LD, LLMs utilize semantic HTML tags to understand document structure:
- `<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`, `<header>`, `<footer>` establish content boundaries.
- `<h1>` through `<h6>` establish topic nesting hierarchy.
- `<table>`, `<dl>`, `<dt>`, `<dd>` provide structured key-value propositions.

---

## 4. Content & Factual Precision Analysis

### 4.1 Proposition Extraction & Ambiguity Detection
LLMs operating over retrieved text are prone to hallucinations when source material is vague, ambiguous, or self-contradictory.
- **Proposition Extraction**: Breaking complex narrative copy into atomic factual propositions (e.g., *"Product X costs \$49/month"*, *"Enterprise plan includes SLA guarantees"*).
- **Contradiction Detection**: Cross-checking propositions extracted across different pages (e.g., Homepage says *"Free 14-day trial"*, while Pricing FAQ says *"Free 30-day trial"*).
- **Distinguishing Marketing Phrasing from Factual Claims**: Evaluators must distinguish between hyperbolic marketing tone (*"The world's most beloved platform"*) and actionable factual assertions (*"Supports up to 10,000 concurrent users"*).

---

## 5. Temporal Signals & Content Freshness

### 5.1 Temporal Metadata Signals
LLM retrieval systems apply recency decay functions when generating answers for time-sensitive domains. The audit checks:
1. **JSON-LD `dateModified`**: Explicit ISO-8601 timestamp representing substantive content revisions.
2. **HTTP `Last-Modified` Header**: Server-level caching and validation header.
3. **XML Sitemap `<lastmod>`**: Timestamp indicating crawl priority.
4. **Visible Timestamp Selectors**: User-facing "Last updated on [Date]" labels.

### 5.2 Handling Evergreen Content
Absence of recent updates on foundational brand pages (e.g., Core Principles, Company Story) must not be penalized if the content is inherently evergreen. Penalties are restricted to time-sensitive assets (product releases, pricing tables, API documentation, news).

---

## 6. On-Site UX, First-Visit Clarity & Engagement Signals

### 6.1 Observable Engagement vs. Private Analytics
Because private analytics (Google Analytics, Mixpanel) cannot be observed from a URL input alone, engagement is inferred from structural, visual, and behavioral friction signals:

| UX Dimension | Observable Technical & Visual Signals | Impact on Visitor & Agent Conversion |
| :--- | :--- | :--- |
| **First-Visit Clarity** | Above-the-fold `<h1>`, subheadline, visual hero preview, value proposition clarity score | Reduces initial bounce and establishes immediate relevance |
| **Content Scannability** | Paragraph lengths (<100 words), heading frequency, bulleted lists, Flesch Reading Ease | Enables fast visual scanning and accurate AI chunking |
| **Navigation & Findability** | Crawl depth to Pricing/Contact (<=2 clicks), clean header/footer menus, internal search form | Eliminates dead-ends and helps visitors locate critical facts |
| **CTA & User Journey** | Button contrast ratio, action-oriented verbs, form field count, functional destination URLs | Minimizes conversion friction and eliminates broken user flows |
| **Mobile Responsiveness** | Viewport meta tag, touch target bounding boxes (>=48px), absence of horizontal overflow | Guarantees accessibility across smartphone viewports |
| **Trust & Credibility** | Accessible Privacy Policy, Terms of Service, physical contact info, verified client proof | Establishes commercial credibility and compliance |
| **WCAG Accessibility** | Form `<label>` associations, image `alt` attributes, accessible button names, contrast >=4.5:1 | Ensures inclusive access for assistive tools and search bots |

---

## 7. AI-Agent Interaction Protocols

### 7.1 The `/llms.txt` and `/llms-full.txt` Specifications
The emerging `/llms.txt` standard provides an intentional, markdown-formatted directory of a website's key content, developer documentation, and core capabilities specifically formatted for LLM context ingestion:
- `/llms.txt`: High-level summary with curated links to essential markdown resources.
- `/llms-full.txt`: Consolidated full-text markdown corpus of documentation for instant context ingestion.

### 7.2 Programmatic Agent Discovery (OpenAPI & Search APIs)
Autonomous AI agents require transparent mechanisms to search and interact with web services:
- Discoverable OpenAPI schemas (`/openapi.json`, `/.well-known/openapi.yaml`).
- Predictable URL search query structures (e.g., `/search?q={query}`).
- Clean semantic container attributes (`data-component`, `data-testid`) that allow headless agents to interact with forms reliably.

---

## 8. Evaluated Tools & Technical Libraries

| Tool / Library | Category | Evaluation Status | Purpose in Engine |
| :--- | :--- | :--- | :--- |
| **Playwright** | Headless Browser Automation | **Selected** | Executes full JavaScript rendering, captures post-hydration DOM, takes viewport screenshots, records Core Web Vitals. |
| **HTTPX / Requests** | Asynchronous HTTP Client | **Selected** | Rapid fetching of raw HTML payloads, HTTP response headers, robots.txt, and sitemaps. |
| **BeautifulSoup4 / lxml** | HTML & XML Parsing | **Selected** | Fast DOM tree traversal, tag extraction, heading hierarchy analysis, and sitemap parsing. |
| **extruct / W3C Schema Tools** | Schema & Metadata Extraction | **Selected** | Extracts JSON-LD, Microdata, OpenGraph, and Twitter card metadata. |
| **textstat** | Readability Metrics | **Selected** | Computes Flesch Reading Ease, Flesch-Kincaid Grade Level, and Gunning-Fog Index. |
| **Pydantic v2** | Data Modeling & Validation | **Selected** | Enforces strict schemas for Evidence Store artifacts, findings, and scoring outputs. |

---

## 9. References & Standards Bibliography

1. **Schema.org Community Group**: *Schema.org Vocabulary & JSON-LD Implementation Guidelines*, 2026. [https://schema.org](https://schema.org)
2. **The llms.txt Proposal**: *A Standard for Machine-Readable Website Summaries*, 2024–2026. [https://llmstxt.org](https://llmstxt.org)
3. **W3C Web Accessibility Initiative (WAI)**: *Web Content Accessibility Guidelines (WCAG) 2.1 AA Specification*, 2023. [https://www.w3.org/TR/WCAG21/](https://www.w3.org/TR/WCAG21/)
4. **Google Search Central**: *Robots.txt Specifications, Canonicalization Best Practices, and Core Web Vitals*, 2025–2026. [https://developers.google.com/search](https://developers.google.com/search)
5. **OpenAI Platform Documentation**: *GPTBot & OAI-SearchBot Web Crawler Specifications*, 2025. [https://platform.openai.com/docs/bots](https://platform.openai.com/docs/bots)
6. **Anthropic Documentation**: *ClaudeBot Web Indexing & Crawler Guidelines*, 2025. [https://support.anthropic.com](https://support.anthropic.com)
7. **Perplexity AI**: *PerplexityBot Indexing & Generative Answer Grounding*, 2025.
