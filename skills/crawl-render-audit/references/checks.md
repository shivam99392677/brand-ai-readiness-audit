# Crawl & Render Audit - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| CR-001 | HTTP Response Status | High / Info | Verifies 200 OK HTTP response code |
| CR-002 | AI Crawler Robots Directives | High / Info | Inspects X-Robots-Tag headers for noindex directives |
| CR-003 | Pre-Rendering Content Availability | Medium / Info | Detects empty container divs indicating JS rendering dependence |
| CR-004 | Text Extractability & Word Boundaries | Medium / Info | Detects suspicious word-boundary collapse |
| CR-005 | Page Title Presence & Quality | Medium / Low / Info | Validates <title> tag presence and descriptive length |
| CR-006 | Meta Description Presence | Low / Info | Checks for <meta name="description"> tag content |
| CR-007 | Heading Structure & H1 Quality | Medium / Low / Info | Audits H1 count, heading hierarchy, and malformed H1 text |
| CR-008 | Discoverable Internal Links | Low / Info | Discovers <a href> internal links for crawler traversal |
| CR-009 | Canonical URL Declaration | Low / Info | Verifies <link rel="canonical"> presence and target alignment |
| CR-010 | Site-Wide Content Discoverability | Medium / Info | Evaluates site-wide content coverage across page roles |
| CR-011 | Raw vs Rendered Text Discrepancy | Medium / Info / N/A | Compares raw pre-rendered text length vs rendered DOM text length |
| CR-012 | Site Crawl Coverage | Low / Info | Audits total pages discovered vs crawled, page roles, and depth bounds |

## Guardrails
- Robots.txt 404/403/timeout is reported as LOW, never as AI Bot Blocking.
- JS-shell protection: pages with <80 visible words not penalized under EG-01.
