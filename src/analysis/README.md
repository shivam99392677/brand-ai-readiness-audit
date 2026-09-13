# `src/analysis/` — Audit Skills

**Business logic:** each file answers one brand-manager question: *Can AI bots reach my site? Read it? Extract structured facts? Is content trustworthy? Is brand identity unambiguous? Does the page convert?* A skill may only publish a finding backed by quoted page evidence; severity inflation is treated as a bug equal to a missed defect (Round 3 QA removed false "AI Bot Blocking" and "missing sameAs" findings).

**Tech logic:** every skill exposes `run_<skill>(evidence: ExtractionResult, website: WebsiteEvidence) -> List[Finding]`. Skills never fetch pages (except the two extended reach skills, which fetch one small root file) — they consume canonical evidence from `src/extraction/`. `PASS`/`INFO` results are emitted too, so reports show what was checked and found healthy.

```mermaid
flowchart LR
    EV["ExtractionResult (CanonicalEvidence items)"] --> CR["crawl_render_audit CR-001..CR-012"]
    EV --> SD["structured_data_audit SD-001..SD-006"]
    EV --> FQ["fact_quality_audit FQ-01..FQ-04"]
    EV --> FC["freshness_corroboration FC-01..FC-03"]
    EV --> EI["entity_identity_audit EI-01..EI-03"]
    EV --> EG["engagement_audit EG-01..EG-04"]
    ROBOTS["robots.txt / sitemap.xml fetch"] --> SM["sitemap_audit CR-013"]
    ROBOTS --> BB["bot_block_audit CR-014"]
    CR & SD & FQ & FC & EI & EG & SM & BB --> OUT["Finding objects -> composer"]
```

### `crawl_render_audit.py` (CR-001 … CR-012)
**Business:** proves AI crawlers can physically get the content: right status code, real `<title>`/meta, meaningful headings, text that doesn't collapse into `pricingPricingAtlas`, canonical declared, internal links discoverable.
**Tech:** an in-file HTMLParser subclass walks the DOM once; CR-004 compares raw vs whitespace-normalized text lengths to catch word-boundary collapse; CR-005 falls back to the crawl-manifest title when the strict `<head><title>` parse misses (fix for the false "missing title" on wikipedia.org).

```mermaid
flowchart TD
    H["raw HTML"] --> P["AuditHTMLParser (html.parser)"]
    P --> T1["CR-001 status / CR-002 x-robots-tag / CR-003 empty-div JS shell"]
    P --> T2["CR-004 word-boundary collapse check"]
    P --> T3["CR-005 title (parser, then crawl-manifest fallback)"]
    P --> T4["CR-006 meta description / CR-007 H1 audit / CR-009 canonical"]
    P --> T5["CR-008 internal links / CR-010 word count / CR-011 raw vs rendered / CR-012 coverage"]
    T2 & T3 & T4 & T5 --> F["Findings with Evidence{observed, location}"]
```

### `structured_data_audit.py` (SD-001 … SD-006)
**Business:** structured data is what lets an AI answer "what does this cost?" — broken JSON-LD on a product page is a revenue defect, while *absent* schema on a blog/homepage is not a defect (Adobe rule; enforced).
**Tech:** extracts `script[type="application/ld+json"]`, parses each with `json.loads` (SD-002 captures the exact parse error + raw snippet), detects `@type`s (SD-003), validates core identity fields on Organization/Product entities (SD-004), compares schema names to visible title/H1 (SD-005), flags conflicting duplicate declarations (SD-006).

```mermaid
flowchart TD
    H["HTML"] --> X["find all ld+json scripts"]
    X -->|"none + non-product page"| NA["SD-001 NOT_APPLICABLE — not a defect"]
    X -->|"none + product page"| P["SD-003 warn: Product fields missing"]
    X --> B{"json.loads each block"}
    B -->|"ok"| TY["SD-003 types / SD-004 fields / SD-006 duplicates"]
    B -->|"error"| ERR["SD-002 HIGH: quote parse_error + raw_snippet"]
    TY & ERR --> F["Findings"]
```

### `fact_quality_audit.py` (FQ-01 … FQ-04)
**Business:** AI assistants quote your numbers back. If `/pricing` says $10 and `/docs` says $25, the model contradicts itself or refuses to answer — a content defect, not an SEO nit.
**Tech:** regex extraction of prices / refund windows / founding years / opening hours per URL; FQ-02 reports a contradiction only when value sets genuinely differ (subset relations tolerated). Two Round-3 fixes: (1) magnitude guard — `$1.9tn`, `$40bn` are monetary magnitudes, not offer prices; (2) cross-currency guard — a ₹ set vs a $ set is regional pricing, not a contradiction.

```mermaid
flowchart TD
    TXT["paragraph / heading / blockquote text per URL"] --> RE["regex: PRICE, REFUND, FOUNDED, HOURS"]
    RE --> MAG{"tail after match = tn/bn/million/k?"}
    MAG -->|"yes"| SKIP["skip — magnitude, not a price"]
    MAG -->|"no"| PC["price_claims url += value"]
    PC --> CMP{"compare page pairs"}
    CMP -->|"one page subset of other"| OK["no finding — superset is consistent"]
    CMP -->|"currencies disjoint"| LOC["skip — regional pricing"]
    CMP -->|"same currency, different values"| F02["FQ-02 HIGH: both URLs + prices + EV ids"]
    TXT --> SUP["superlative with no nearby citation"] --> F04["FQ-04 MEDIUM with snippet"]
    TXT --> UN["numbers without units or baseline"] --> F03["FQ-03"]
```

### `freshness_corroboration.py` (FC-01 … FC-03)
**Business:** recency is a ranking and citation signal; conflicting dates erode trust; content older than 12 months decays in generative answers; `sameAs`/Wikidata let a model verify *who* you are. Footer `© 2024` is explicitly NOT staleness evidence.
**Tech:** collects `FRESHNESS_DATE` evidence (Last-Modified, JSON-LD dates, `<time datetime>`, visible dates) per URL; FC-01 flags year-level disagreement between source types; FC-02 flags staleness only from explicit timestamps; FC-03 verifies sameAs/Wikidata reachability and only raises a LOW suggestion when an Organization entity is actually declared — never on placeholder domains.

```mermaid
flowchart TD
    D["FRESHNESS_DATE evidence per URL"] --> F1{"sources disagree on year?"}
    F1 -->|"yes"| A["FC-01: visible vs schema vs Last-Modified"]
    D --> F2{"newest explicit date older than 365d?"}
    F2 -->|"yes"| B["FC-02 stale content (copyright years ignored)"]
    SA["sameAs + Wikidata evidence"] --> F3{"declared links exist?"}
    F3 -->|"404"| C1["FC-03 HIGH: broken KG link"]
    F3 -->|"present"| C2["FC-03 PASS info"]
    F3 -->|"none + Organization declared"| C3["FC-03 LOW suggestion"]
    F3 -->|"none + no Organization"| C4["skip — absence is not a trust failure"]
```

### `entity_identity_audit.py` (EI-01 … EI-03)
**Business:** if schema says one brand name, the `<title>` another, and the footer phone differs per page, an AI cannot form one confident entity — answers fragment.
**Tech:** collects `ENTITY_NAME/PHONE/ADDRESS` + titles + H1s; EI-01 conflicts only between *root brand* names (Round-3 fix: FAQ-question strings like "Do you have setup fees?" and branch names like "Stripe Berlin" collapse away first); EI-02 validates sameAs URLs (format → HTTP) and stays silent when no Organization exists; EI-03 compares normalized phone/address sets across pages.

```mermaid
flowchart TD
    N["ENTITY_NAME evidence"] --> Q{"name contains '?' (FAQ heading)?"}
    Q -->|"yes"| DROP["drop from brand set"]
    Q -->|"no"| BR{"multi-word name starting with declared single-word brand?"}
    BR -->|"yes, e.g. Stripe Berlin"| DROP
    BR -->|"no"| ROOTS["root brand names"]
    ROOTS -->|"2+ distinct"| E1["EI-01 HIGH name discrepancy"]
    ROOTS -->|"1 root vs title mismatch"| E1B["EI-01 brand_title_mismatch"]
    SA["sameAs links"] --> E2{"urls valid? reachable?"}
    E2 -->|"invalid"| E2A["EI-02 invalid URL"]
    E2 -->|"404"| E2B["EI-02 HIGH broken profile"]
    PH["phones/addresses per page"] --> NORM["normalize digits / address strings"]
    NORM -->|"same entity, different values"| E3["EI-03 HIGH NAP conflict"]
```

### `engagement_audit.py` (EG-01 … EG-04)
**Business:** a human visitor — and the AI mirroring their judgment — must know in one screen who you are, what you offer, and what to do next. A "Learn more" link pointing at itself is a conversion dead end.
**Tech:** EG-01 fires only at ≥80 words of extractable homepage text (a JS shell belongs to the crawl skill — no double counting); EG-02 checks homepage H2 "offerings" are reachable from nav labels; EG-03 walks every crawled interior URL of depth ≥2 (post-fix: including pages with zero links) and treats a link to the parent path as breadcrumb context; EG-04 flags generic anchors looping to the same page or `#`.

```mermaid
flowchart TD
    HOME["homepage headings / paragraphs / links / forms"] --> WC{"home word count >= 80?"}
    WC -->|"no"| SKIP["skip EG-01 — JS shell owned by CR skill"]
    WC -->|"yes"| MISS{"has H1? subhead? action CTA?"}
    MISS -->|"items missing"| E1["EG-01 HIGH: missing Who/What/Next"]
    H2["homepage H2 texts"] --> NAV{"nav labels cover offerings?"}
    NAV -->|"no"| E2["EG-02 MEDIUM"]
    URLS["all crawled interior URLs, depth >= 2"] --> BRD{"breadcrumb anchor/rel OR link to parent path?"}
    BRD -->|"none"| E3["EG-03 MEDIUM with url + path_depth"]
    LNK["links"] --> LOOP{"anchor learn-more AND target == self or empty?"}
    LOOP -->|"yes"| E4["EG-04 MEDIUM cta_loop evidence"]
```

### `sitemap_audit.py` (CR-013, extended skill)
**Business:** a sitemap is bulk discovery for crawlers. Missing one is a *suggestion*, not a site failure — Round-3 QA demoted the old HIGH "expected 200" verdict after example.com and stripe.com showed honest 404s.
**Tech:** fetches `/sitemap.xml` with the audit UA; non-200 → LOW `No Sitemap at /sitemap.xml (HTTP …)` pointing at robots.txt `Sitemap:` declarations; a network timeout is reported *unscored* (ERROR/LOW) — never as a site defect.

```mermaid
flowchart TD
    G["GET base/sitemap.xml"] --> NET{"network ok?"}
    NET -->|"timeout or error"| U["LOW 'Unreachable — not scored' (ERROR status)"]
    NET --> CODE{"status == 200?"}
    CODE -->|"404 / 403"| L["LOW 'No Sitemap at /sitemap.xml' + robots hint"]
    CODE -->|"200"| LOC{"has loc URL entries?"}
    LOC -->|"no"| W["MEDIUM: empty sitemap"]
    LOC -->|"yes"| PASS["PASS info: sitemap present"]
```

### `bot_block_audit.py` (CR-014, extended skill)
**Business:** if GPTBot / ClaudeBot / PerplexityBot are explicitly `Disallow`ed, AI answers cannot cite you at all — the highest-impact reach defect. Conversely a *missing* robots.txt means default rules apply: reporting "AI Bot Blocking" for it is factually false (Round-3 QA removed that verdict).
**Tech:** parses UA groups in order, finds `Disallow: /` under each target bot; explicit block → HIGH FAIL quoting `blocked_bots`; 404/403 → LOW "robots.txt Not Accessible (HTTP …)"; timeout → LOW "not scored".

```mermaid
flowchart TD
    G["GET base/robots.txt"] --> S{"status 200?"}
    S -->|"no"| NOT["LOW 'Not Accessible' — blocking NOT claimed"]
    S -->|"yes"| P["for bot in gptbot, claudebot, perplexitybot, google-extended"]
    P --> D{"User-agent: bot followed by Disallow: / ?"}
    D -->|"yes"| HIGH["HIGH FAIL 'explicitly disallows AI bots' + blocked_bots"]
    D -->|"no"| OK["PASS info: bots not blocked"]
```

### `understanding.py`
**Business:** bridge to a semantic layer (entities/facts above raw text) so future skills can reason about *meaning* instead of strings.
**Tech:** defines `ExtractedEntity` / `ExtractedFact` models and an adapter interface the extraction layer can grow into; deliberately dependency-free today.

```mermaid
flowchart LR
    E["CanonicalEvidence"] --> A["adapter interface"]
    A --> EN["ExtractedEntity(name, type, mentions)"]
    A --> EF["ExtractedFact(subject, predicate, object, source_ev)"]
    EN & EF --> FUTURE["skills that need meaning, not strings"]
```

**Parent:** [src README](../README.md).