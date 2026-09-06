---
name: Crawl & Render Audit
description: Evaluates technical SEO, robots.txt AI bot permissions, HTTP headers, pre-JS vs post-JS rendering parity (DOM delta), XML sitemaps, canonicals, and observable performance.
---

# Crawl & Render Audit Skill

## Purpose
The **Crawl & Render Audit** skill evaluates the fundamental technical infrastructure, machine accessibility, text extractability, and discoverability of a target website. It verifies whether traditional search bots and modern AI crawlers (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Amazonbot`, `Bytespider`) can fetch, render, and index website assets without technical blockages, client-side rendering failures, or redirect loops.

---

## When to Use
Invoked by `audit-orchestrator` during the initial discovery and technical evaluation phase of an audit.

---

## Standard Check Matrix

| Check ID | Title | Category | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`CR-001`** | **HTTP Response Status** | Technical Accessibility | High / Info | Verifies 200 OK HTTP response code. |
| **`CR-002`** | **AI Crawler Robots Directives** | Technical Accessibility | High / Info | Inspects `robots.txt` and `X-Robots-Tag` headers for `noindex`/disallow directives. |
| **`CR-003`** | **Pre-Rendering Content Availability** | Technical Accessibility | Medium / Info | Detects empty container divs indicating JS rendering dependence. |
| **`CR-004`** | **Text Extractability & Word Boundaries** | Extractability | Medium / Info | Detects suspicious word-boundary collapse where words run together. |
| **`CR-005`** | **Page Title Presence & Quality** | Content Structure | Medium / Low / Info | Validates `<title>` tag presence, uniqueness, and descriptive length. |
| **`CR-006`** | **Meta Description Presence** | Content Structure | Low / Info | Checks for `<meta name="description">` tag content and length. |
| **`CR-007`** | **Heading Structure & H1 Quality** | Content Structure | Medium / Low / Info | Audits H1 count, heading hierarchy, and malformed H1 text. |
| **`CR-008`** | **Discoverable Internal Links** | Discoverability | Low / Info | Discovers `<a href>` internal links for crawler traversal. |
| **`CR-009`** | **Canonical URL Declaration** | Content Structure | Low / Info | Verifies `<link rel="canonical">` presence and target alignment. |
| **`CR-010`** | **Site-Wide Content Discoverability** | Content Structure | Medium / Info | Evaluates site-wide content coverage across page roles. |
| **`CR-011`** | **Raw vs Rendered Text Discrepancy** | Extractability | Medium / Info / N/A | Compares raw pre-rendered text length vs rendered DOM text length (DOM Delta). |
| **`CR-012`** | **Site Crawl Coverage** | Discoverability | Low / Info | Audits total pages discovered vs crawled, page roles, and depth bounds. |

---

## High-Level Responsibilities

1. **AI User-Agent & `robots.txt` Directive Parsing**:
   - Parses `robots.txt` against distinct AI crawler User-Agents (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Bytespider`, `Amazonbot`).
   - Flags blanket blocks (`Disallow: /`) and path-specific crawler restrictions.

2. **HTTP Response & Security Header Inspection**:
   - Evaluates HTTP response status codes (200 OK, 301 clean redirects, 404/410 handling).
   - Detects redirect chains (>2 hops) and circular loops.
   - Inspects `X-Robots-Tag` headers for accidental `noindex` / `nofollow` directives.
   - Audits HTTPS enforcement, SSL certificate validity, and `Strict-Transport-Security` (HSTS).

3. **Client-Side Rendering (CSR) vs. Server-Side Rendering (SSR) Parity**:
   - Calculates the **DOM Delta** between raw pre-JavaScript HTML and fully rendered post-JavaScript DOM.
   - Detects if critical product copy, pricing, FAQs, or navigational links are missing in raw HTML.

4. **XML Sitemap & Canonical Tag Verification**:
   - Verifies `sitemap.xml` availability, schema compliance, and status codes of declared URLs.
   - Validates `<link rel="canonical">` implementation to prevent duplicate indexing.

5. **Observable Performance & Core Web Vitals**:
   - Measures TTFB (Time to First Byte), LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift), and Total Blocking Time (TBT).

---

## Code Entrypoint
- Implementation module: [`src/analysis/crawl_render_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/src/analysis/crawl_render_audit.py)
- Unit tests: [`tests/test_crawl_render_audit.py`](file:///c:/Users/ankit/Desktop/brand-ai-readiness-audit/tests/test_crawl_render_audit.py)

---

## Inputs
- **`target_urls`** *(array of strings, required)*: URLs to crawl and analyze.
- **`user_agents`** *(array of strings, optional)*: Specific AI bot User-Agent strings to test against `robots.txt`.

---

## Outputs
- **`technical_score`** *(number, 0–100)*: Normalized Technical SEO & Crawlability score.
- **`findings`** *(array of objects)*: Finding objects containing `finding_id`, `category`, `severity`, `title`, `description`, `impact`, `evidence_ids`, and `remediation`.
- **`dom_delta_report`**: Token count and content parity metrics across raw vs rendered DOM.

---

## Evidence Expectations
- `EVID-ROBOTS-TXT`: Raw `robots.txt` content and parsed AST per User-Agent.
- `EVID-HTTP-HEADERS`: HTTP status codes, redirect traces, and response headers.
- `EVID-DOM-RAW`: Un-hydrated raw HTML payload.
- `EVID-DOM-RENDERED`: Fully hydrated post-JS DOM snapshot.
- `EVID-SITEMAP-XML`: Sitemap fetch responses and URL status logs.
- `EVID-PERF-METRICS`: Observable browser timing metrics (LCP, CLS, TTFB, TBT).

---

## False-Positive Considerations
- **Staging / Preview Environments**: `Disallow: /` on staging subdomains is intentional and should not be penalized if auditing a live production domain.
- **Anti-DDoS / Rate Limiting**: Cloudflare challenge pages encountered during automated crawling should be flagged as access limitations rather than site-wide `robots.txt` blocks.
- **Selective Training Bot Restrictions**: A brand may intentionally disallow training bots (e.g., `Bytespider`) while permitting search bots (`PerplexityBot`). This should be reported as an intentional choice with Medium/Informational severity rather than a Critical failure.
