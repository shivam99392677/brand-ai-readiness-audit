# `src/crawler/` — Discovery & Fetch Layer

**Business logic:** this layer decides *what the auditor sees*, and therefore what it is allowed to claim. It respects robots.txt like a polite AI crawler would, discovers pages through sitemaps and links, and fetches enough raw HTML to judge content honestly. Its "HTTP-first, render-only-when-needed" strategy keeps a 15-page audit cheap enough that content quality — not browser overhead — stays the point.

**Tech logic:** bounded priority-queue crawl. Robots are fetched and parsed first, sitemaps seed discovery, URLs are scored deterministically, pages are fetched with `requests` (raw HTML = what an AI crawler gets), and only pages whose raw HTML looks empty/JS-shell get considered for Playwright rendering, capped by `max_rendered_pages`. Everything a page yields (status, headers, HTML, title, word count, contacts, schema) lands in a `CrawlManifest`.

```mermaid
flowchart TD
    START["start URL"] --> RB["RobotsChecker.fetch_and_parse"]
    RB --> SM["SitemapDiscoverer (robots-declared + /sitemap.xml)"]
    SM --> PQ["priority queue (prioritizer.py)"]
    PQ --> LOOP{"queue not empty AND pages < max_pages?"}
    LOOP -->|"yes"| ALLOWED{"robots_checker.is_allowed(url)?"}
    ALLOWED -->|"no"| SKIPPED["skipped_urls: blocked_by_robots_txt"]
    ALLOWED -->|"yes"| FETCH["requests.get (audit User-Agent)"]
    FETCH --> RD{"render_decision.should_render_page?"}
    RD -->|"yes AND render budget left"| PW["BrowserRenderer (Playwright)"]
    RD -->|"no"| RAW["keep raw HTTP HTML"]
    PW & RAW --> META["extract title / meta / links / content / contacts / schema"]
    META --> MANIFEST["CrawlManifest.pages + website_evidence"]
    MANIFEST --> LOOP
    LOOP -->|"no"| DONE["manifest -> ExtractionManager"]
```

### `engine.py`
**Business:** the budgeted crawl loop — the difference between auditing 15 pages in 40 seconds and hammering a site for minutes.
**Tech:** `SiteCrawler(config: CrawlConfig)` orchestrates robots → sitemap → per-page fetch/extract/render; honors `same_domain_only`, `respect_robots`, `max_requests_per_second`; records `failed_urls`, `skipped_urls`, truncation reason; exposes `html_override`/`custom_fetcher` hooks for offline fixture tests.

```mermaid
flowchart TD
    C["CrawlConfig: max_pages, max_depth, respect_robots, user_agent"] --> CS["SiteCrawler.crawl_site(start_url)"]
    CS --> R1["robots evidence -> robots_info"]
    R1 --> R2["sitemap seed URLs"]
    R2 --> W["while-loop over priority queue"]
    W --> EX["per-page extract_* collectors"]
    EX --> EV["WebsiteEvidence + per-page evidence dicts"]
    EV --> M["CrawlManifest(pages, robots_status, sitemap_status, truncated, failed_urls)"]
```

### `robots.py`
**Business:** the auditor must obey — and report — the same robot rules a real GPTBot would see. A `Disallow: /` for `GPTBot` is the single most important reach finding.
**Tech:** `RobotsChecker.fetch_and_parse()` builds structured `RobotsEvidence` (available, status, UA groups, sitemap declarations); `is_allowed(url, evidence)` evaluates the longest-match UA group with `*` fallback.

```mermaid
flowchart TD
    F["GET /robots.txt"] --> P["parse User-agent groups in order"]
    P --> G["group per UA: '*', 'GPTBot', 'ClaudeBot', 'PerplexityBot'"]
    G --> D["collect Disallow / Allow lines + Sitemap: declarations"]
    D --> E["RobotsEvidence(available, status_code, sitemaps_declared)"]
    E --> Q{"is_allowed(url): matching group disallows path?"}
    Q -->|"yes"| NO["False -> crawler skips, records skipped_url"]
    Q -->|"no"| YES["True -> fetch"]
```

### `sitemap.py`
**Business:** sitemaps reveal canonical URLs the homepage never links — critical for docs and storefronts with deep product pages.
**Tech:** `SitemapDiscoverer.discover_sitemap_urls()` checks robots-declared sitemaps plus `/sitemap.xml`, parses `<urlset>` and `<sitemapindex>` (child sitemaps recursed), returns `SitemapEvidence` + discovered URLs into the crawl frontier.

```mermaid
flowchart TD
    S1["candidates: robots-declared + /sitemap.xml"] --> S2["GET each"]
    S2 --> IX{"sitemapindex element?"}
    IX -->|"yes"| REC["recurse into child sitemaps"]
    IX -->|"no, urlset element"| U["collect loc URLs"]
    REC --> U
    U --> EV["SitemapEvidence + discovered URLs"]
```

### `prioritizer.py`
**Business:** with a page budget, the auditor must spend it where the brand value is: homepage, product/pricing/about — not calendar archives.
**Tech:** `calculate_url_priority(url, anchor_text)` — deterministic scoring from path depth, path keywords (`product`, `pricing`, `about`, `contact`), and anchor text; no ML, no randomness, so audits are reproducible.

```mermaid
flowchart LR
    U["candidate URL + anchor text"] --> S["path depth score"]
    U --> K["keyword score (product/pricing/about/contact/docs)"]
    U --> A["anchor text score"]
    S & K & A --> T["total priority int"]
    T --> Q["priority queue order"]
```

### `render_decision.py`
**Business:** JS-heavy homepages look empty to crawlers; but rendering every page is expensive. The decision engine limits browser work to pages that need it.
**Tech:** `should_render_page(html, url)` — heuristic thresholds (raw text length, script-to-text ratio, empty-container signals) → `RenderDecision.required`; the engine additionally caps rendered pages (`max_rendered_pages`) and never re-renders `html_override` fixtures.

```mermaid
flowchart TD
    H["raw HTML"] --> T{"visible text < threshold OR script/text ratio high OR empty divs?"}
    T -->|"yes"| Y["RenderDecision.required = True"]
    T -->|"no"| N["False — raw HTML is representative"]
    Y --> BUD{"render budget remaining?"}
    BUD -->|"yes"| PLAY["Playwright render"]
    BUD -->|"no"| KEEP["use raw HTML, note truncation"]
```

### `browser.py`
**Business:** the fallback "what a human sees" extractor for JS shells — used sparingly.
**Tech:** `BrowserRenderer.render_page(url)` wraps isolated Playwright Chromium; returns `RenderedPageResult` (rendered HTML, text length, status) or a failure record that never destroys the raw HTTP evidence already collected.

```mermaid
flowchart TD
    R["render_page(url)"] --> LW["launch Chromium context"]
    LW --> G["goto(url), wait for network idle"]
    G --> OK{"success?"}
    OK -->|"yes"| RES["RenderedPageResult(html, text_length, status)"]
    OK -->|"no"| FAIL["failure record — raw HTTP evidence preserved"]
```

### `role_classifier.py`
**Business:** a defect on a *product* page (missing price schema) is not the same as one on a *legal* page (no CTA). Page roles let skills apply the right rule to the right page.
**Tech:** `classify_page_role_signals()` — deterministic classification from URL path, title, headings, and anchor text into roles: `homepage`, `about`, `contact`, `product`, `pricing`, `terms`, `documentation`, `other`; returns structured `PageRoleSignals` (default `unknown` when nothing matches).

```mermaid
flowchart LR
    S["url path + title + h1 + anchors"] --> M{"keyword / structure match"}
    M --> H["homepage"] & P["product / pricing"] & A["about / contact"] & T["terms / privacy"] & D["documentation"]
    M --> O["other / unknown"]
    H & P & A & T & D & O --> SIG["PageRoleSignals -> evidence + skill scoping"]
```

### `url_utils.py`
**Business:** the auditor must never crawl the same page twice or leak off-domain — duplicate findings and out-of-scope fetches both undermine trust in the report.
**Tech:** `normalize_url()` (resolve relative, strip fragments, lowercase host, standardize slashes), same-domain verification, base-domain extraction, dedup keys used by the engine's visited set.

```mermaid
flowchart TD
    IN["raw href"] --> N["normalize_url: resolve relative, strip #fragment, lowercase host, fix slashes"]
    N --> SAME{"same registrable domain as start?"}
    SAME -->|"no"| X["external — do not enqueue"]
    SAME -->|"yes"| D{"already visited?"}
    D -->|"yes"| X2["dedup"]
    D -->|"no"| Q["enqueue with priority"]
```

**Parent:** [src README](../README.md).
