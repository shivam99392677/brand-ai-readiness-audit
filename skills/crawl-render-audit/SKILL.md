---
name: crawl-render-audit
description: Evaluates HTTP status, robots directives, DOM text extractability, heading hierarchy, link discoverability, site crawl coverage, and SSR/CSR parity.
---

# Crawl & Render Audit Skill

## Purpose
Audits the technical accessibility, text extractability, content structure, and discoverability of web pages for automated AI systems and web crawlers.

## Key Dimension Classifications
1. **Technical Accessibility**: Evaluates HTTP response codes (`CR-001`), robots headers (`CR-002`), and pre-render payload availability (`CR-003`).
2. **Text Extractability**: Evaluates text whitespace/word-boundary integrity (`CR-004`) and raw vs rendered text length parity (`CR-011`).
3. **Content Structure**: Evaluates page title presence (`CR-005`), meta descriptions (`CR-006`), heading hierarchy and malformed H1 text (`CR-007`), canonical URLs (`CR-009`), and structural sections (`CR-010`).
4. **Discoverability**: Evaluates internal link discovery (`CR-008`) and site crawl coverage (`CR-012`).

## Standard Check Matrix

| Check ID | Title | Category | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`CR-001`** | **HTTP Response Status** | Technical Accessibility | High / Info | Verifies 200 OK HTTP response code. |
| **`CR-002`** | **AI Crawler Robots Directives** | Technical Accessibility | High / Info | Inspects `X-Robots-Tag` headers for `noindex` directives. |
| **`CR-003`** | **Pre-Rendering Content Availability** | Technical Accessibility | Medium / Info | Detects empty container divs indicating JS rendering dependence. |
| **`CR-004`** | **Text Extractability & Word Boundaries** | Extractability | Medium / Info | Detects suspicious word-boundary collapse where words run together. |
| **`CR-005`** | **Page Title Presence & Quality** | Content Structure | Medium / Low / Info | Validates `<title>` tag presence and descriptive length. |
| **`CR-006`** | **Meta Description Presence** | Content Structure | Low / Info | Checks for `<meta name="description">` tag content. |
| **`CR-007`** | **Heading Structure & H1 Quality** | Content Structure | Medium / Low / Info | Audits H1 count, heading hierarchy, and malformed H1 text. |
| **`CR-008`** | **Discoverable Internal Links** | Discoverability | Low / Info | Discovers `<a href>` internal links for crawler traversal. |
| **`CR-009`** | **Canonical URL Declaration** | Content Structure | Low / Info | Verifies `<link rel="canonical">` presence and target alignment. |
| **`CR-010`** | **Site-Wide Content Discoverability** | Content Structure | Medium / Info | Evaluates site-wide content coverage across page roles. |
| **`CR-011`** | **Raw vs Rendered Text Discrepancy** | Extractability | Medium / Info / N/A | Compares raw pre-rendered text length vs rendered DOM text length. |
| **`CR-012`** | **Site Crawl Coverage** | Discoverability | Low / Info | Audits total pages discovered vs crawled, page roles, and depth bounds. |

## Code Entrypoint
- Implementation module: [`src/analysis/crawl_render_audit.py`](../../src/analysis/crawl_render_audit.py)
- Unit tests: [`tests/test_crawl_render_audit.py`](../../tests/test_crawl_render_audit.py)
