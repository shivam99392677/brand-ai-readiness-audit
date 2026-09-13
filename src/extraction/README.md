# `src/extraction/` — Canonical Evidence Layer

**Business logic:** this folder converts raw crawl artifacts into *facts a human can re-find in 30 seconds*. It contains **no opinions** — no findings, scores, or severity. That separation is the product's honesty guarantee: when a report says "parse_error: Expecting ',' delimiter … raw_snippet: `{ "name": "Pro"`", that sentence was produced here, as data, before any skill judged it. Round-3 QA findings ("evidence is only `observed: {same_as_count: 0}`") are enforced at this layer: evidence must carry a URL, a count, or a quoted snippet.

**Tech logic:** `ExtractionManager.extract(crawl_manifest)` fans a `CrawlManifest` out to specialized extractors. Each extractor emits `CanonicalEvidence` records (Pydantic) with a central `EvidenceIdGenerator` ID (`EV-00001`…), an `EvidenceType` from `src/shared/evidence_schema.py`, and a `Provenance` pointer (source, URL, location, selector). Errors are recorded as `ExtractionError` records, never exceptions — one broken page cannot break the audit.

```mermaid
flowchart TD
    M["CrawlManifest (pages: html, headers, status, title, meta, links, robots, sitemaps)"] --> EM["ExtractionManager.extract()"]
    EM --> H["HTTPExtractor"]
    EM --> MD["MetadataExtractor + metadata.py"]
    EM --> T["TextExtractor + page.py"]
    EM --> L["LinkExtractor + links.py + images.py"]
    EM --> S["SchemaExtractor + structured_data.py"]
    EM --> R["RobotsExtractor + resource_extractor.py"]
    EM --> E["EntityExtractor"]
    EM --> F["FreshnessExtractor"]
    EM --> SI["SiteExtractor + media_extractor.py"]
    H & MD & T & L & S & R & E & F & SI --> ID["EvidenceIdGenerator.next_id() -> EV-00001.."]
    ID --> RES["ExtractionResult(evidence[], errors[], metadata)"]
```

### `extraction_manager.py`
**Business:** the single coordinator that turns "a folder of fetched pages" into "an ordered evidence store" — the input contract all six audit skills share.
**Tech:** iterates manifest pages + robots/sitemap artifacts, invokes each extractor, aggregates results into one `ExtractionResult` with sequential evidence IDs and non-fatal error records.

```mermaid
flowchart TD
    IN["CrawlManifest"] --> PG{"for page in pages"}
    PG --> CALL["run extractor set for this page"]
    CALL --> AGG["aggregate evidence + errors"]
    AGG --> METRICS["metadata: counts, timing"]
    METRICS --> OUT["ExtractionResult"]
```

### `id_generator.py`
**Business:** every evidence item must be citable — "both prices in evidence ([EV-00024], [EV-00035])" only works if IDs exist and are stable.
**Tech:** `EvidenceIdGenerator(prefix="EV-", digits=5, start=1)` — deterministic, in-run sequential `next_id()`; one generator instance is shared by all extractors so IDs never collide.

```mermaid
flowchart LR
    C["EvidenceIdGenerator EV-, 5 digits"] --> N1["next_id -> EV-00001"]
    N1 --> N2["next_id -> EV-00002"]
    N2 --> NX["next_id -> EV-000NN"]
    NX --> CITE["quoted in Finding evidence strings"]
```

### `http_extractor.py`
**Business:** proves the page was actually reachable and describes *how* it responded — the "status a human can re-find" part of evidence.
**Tech:** `HTTPExtractor.extract_http_evidence()` — status code/reason, headers of interest (x-robots-tag, content-type), redirect chains, response timing → `HTTP_STATUS` / `HTTP_HEADER` / `HTTP_REDIRECT` evidence.

```mermaid
flowchart LR
    P["page: status + headers"] --> A["status_code + reason -> HTTP_STATUS"]
    P --> B["x-robots-tag, content-type -> HTTP_HEADER"]
    P --> C["redirect chain -> HTTP_REDIRECT"]
    P --> D["response timing -> RESPONSE_TIMING"]
    A & B & C & D --> OUT["CanonicalEvidence records"]
```

### `metadata_extractor.py` + `metadata.py`
**Business:** title, meta description, canonical, OpenGraph — the elements AI systems quote verbatim when summarizing a brand.
**Tech:** `MetadataExtractor.extract_metadata_evidence(url, html…)` parses `<head>` for `<title>`, `meta[name=description]`, `link[rel=canonical]`, language/charset/viewport, plus OG/Twitter tags (via `metadata.py` helpers); emits `PAGE_METADATA`, `CANONICAL_URL`, `OPENGRAPH_META`, `TWITTER_META`, `VIEWPORT_META` evidence.

```mermaid
flowchart TD
    H["head section HTML"] --> T["title element -> PAGE_METADATA(title)"]
    H --> D["meta description -> PAGE_METADATA(meta_description)"]
    H --> C["link rel=canonical -> CANONICAL_URL"]
    H --> O["meta property og:* -> OPENGRAPH_META(fields)"]
    H --> TW["meta name=twitter:* -> TWITTER_META"]
    H --> V["charset / viewport / language metas"]
    T & D & C & O & TW & V --> E["evidence with location pointer in head section"]
```

### `link_extractor.py` + `links.py` + `images.py`
**Business:** internal links are the roads a crawler (human or AI) can drive; images and downloads are extractable brand assets. Counts here feed the crawl budget and the "Discoverable Internal Links" finding.
**Tech:** `LinkExtractor.extract_link_evidence()` (over `links.py`) normalizes anchors into `LINK_ITEM`/`INTERNAL_LINK`/`EXTERNAL_LINK`/`DOCUMENT_RESOURCE` evidence with `anchor_text`, `target_url`, `is_internal`, `rel`; `images.py` classifies `<img>`/og:image into `IMAGE_ITEM` with declared vs resolved URLs and flags 1×1 pixels as tracking.

```mermaid
flowchart TD
    H["page HTML"] --> A["anchor href tags -> normalize target"]
    A --> I{"internal (same domain)?"}
    I -->|"yes"| IL["INTERNAL_LINK(anchor_text, target_url)"]
    I -->|"no"| EL["EXTERNAL_LINK"]
    A --> D{"href ends .pdf/.doc/…?"}
    D -->|"yes"| DR["DOCUMENT_RESOURCE"]
    H --> IMG["img / og:image tags -> IMAGE_ITEM(declared_url, resolved_url, dims)"]
    IMG --> TR{"width=1 height=1 or 'tracking' in name?"}
    TR -->|"yes"| TRK["flag is_tracking"]
    IL & EL & DR & IMG & TRK --> E["evidence + crawl-frontier targets"]
```

### `schema_extractor.py` + `structured_data.py`
**Business:** the structured-data layer is where "what does this cost / who are you" becomes machine-readable. This extractor captures JSON-LD **raw payloads** and parse errors so SD-002 can quote the defect exactly.
**Tech:** `SchemaExtractor.extract_schema_evidence()` (over `structured_data.py`) finds `script[type="application/ld+json"]`, attempts `json.loads` per block, records success (`JSONLD_PARSED` with `@type`s) or failure (`JSONLD_PARSE_ERROR` with the exact error string + raw snippet), plus Microdata `itemtype` elements.

```mermaid
flowchart TD
    H["page HTML"] --> F["find application/ld+json script blocks"]
    F --> J{"json.loads each block"}
    J -->|"ok"| P["JSONLD_PARSED(types, entities) + SCHEMA_TYPE records"]
    J -->|"error"| ERR["JSONLD_PARSE_ERROR(parse_error, raw_snippet, script_index)"]
    H --> M["microdata itemtype elements -> MICRODATA_ITEM"]
    P & ERR & M --> E["evidence -> structured_data_audit"]
```

### `text_extractor.py` + `page.py`
**Business:** the "read" question: is there real extractable text, in the right structure (H1/H2 hierarchy), without words fusing together — and does raw HTML agree with any rendered DOM?
**Tech:** `TextExtractor.extract_text_evidence()` (over `page.py` DOM walking) produces headings with levels, paragraphs, list/table/blockquote/FAQ blocks, a `VISIBLE_TEXT_SUMMARY` with word counts per section, and `TEXT_EXTRACTABILITY_SIGNAL` recording raw vs normalized lengths and word-boundary collapse detection.

```mermaid
flowchart TD
    H["page HTML (raw or rendered)"] --> W["walk DOM text nodes + block elements"]
    W --> HH["h1..h6 -> HEADING{level, text}"]
    W --> P["paragraph element -> PARAGRAPH(text)"]
    W --> B["ul/table/blockquote/figure -> LIST/TABLE/BLOCKQUOTE/CAPTION/FAQ blocks"]
    W --> WC["word count per section -> VISIBLE_TEXT_SUMMARY"]
    W --> X{"normalized length << raw length?"}
    X -->|"yes"| COL["TEXT_EXTRACTABILITY_SIGNAL: collapse detected + suspicious tokens"]
    X -->|"no"| OK["signal: boundaries preserved"]
    HH & P & B & WC & COL & OK --> E["evidence records"]
```

### `robots_extractor.py` + `resource_extractor.py`
**Business:** reach rules (robots directives) and machine manifests (sitemaps) are fetched facts — recorded here so reach findings quote real lines rather than categories.
**Tech:** `RobotsExtractor` normalizes robots evidence into `ROBOTS_RULE` / `ROBOTS_SITEMAP_DECLARATION` / `ROBOTS_CRAWL_DELAY` records; `ResourceExtractor.extract_sitemap_evidence()` emits `SITEMAP_ENTRY` records (and probes optional machine manifests when present).

```mermaid
flowchart TD
    RB["RobotsEvidence from crawler"] --> P["rules -> ROBOTS_RULE{ua, directive, path}"]
    RB --> SD["Sitemap: lines -> ROBOTS_SITEMAP_DECLARATION"]
    RB --> CD["Crawl-delay -> ROBOTS_CRAWL_DELAY"]
    SM["sitemap XML"] --> SE["loc entries -> SITEMAP_ENTRY"]
    P & SD & CD & SE --> E["reach evidence records"]
```

### `entity_extractor.py`
**Business:** brand identity facts — names, addresses, phones, emails, logos, sameAs/Wikidata links — are what let an AI verify *who* the brand is. Pulled from JSON-LD, microdata, and visible contact text.
**Tech:** emits `ENTITY_NAME` / `ENTITY_ADDRESS` / `ENTITY_PHONE` / `ENTITY_EMAIL` / `ENTITY_LOGO` / `SAME_AS_LINK` / `WIKIDATA_ID` / `ENTITY_IDENTIFIER` evidence with per-item location pointers (schema path or DOM context).

```mermaid
flowchart TD
    S["JSON-LD / microdata entities"] --> N["name -> ENTITY_NAME"]
    S --> AD["address -> ENTITY_ADDRESS"]
    S --> PH["telephone -> ENTITY_PHONE"]
    S --> EM["email / logo / identifier"]
    S --> SA["sameAs array -> SAME_AS_LINK(url)"]
    S --> WK["wikidata refs -> WIKIDATA_ID"]
    DOM["visible contact text"] --> PHD["phone/address/email candidates"]
    N & AD & PH & EM & SA & WK & PHD --> E["entity evidence -> entity_identity_audit"]
```

### `freshness_extractor.py`
**Business:** recency claims must be captured from every source a date can hide in — headers, schema, `<time>` tags, visible text — so date conflicts and staleness are judged from facts, and footer `© 2024` is never mistaken for content age.
**Tech:** emits `FRESHNESS_DATE` records with the source type (http_last_modified, jsonld_date, time_tag, visible_date), the ISO value, and the raw string; copyright-year hits carry a type flag that staleness checks ignore.

```mermaid
flowchart TD
    HM["Last-Modified header"] --> D1["FRESHNESS_DATE(source http_last_modified)"]
    J["JSON-LD datePublished / dateModified"] --> D2["FRESHNESS_DATE(source jsonld_date)"]
    T["time tag with datetime attribute"] --> D3["FRESHNESS_DATE(source time_tag)"]
    V["visible date strings"] --> D4["FRESHNESS_DATE(source visible_date)"]
    FY["© year / 'since 2020' in body"] --> IGN["captured with copyright flag — staleness ignores it"]
    D1 & D2 & D3 & D4 & IGN --> E["freshness evidence -> freshness_corroboration"]
```

### `site_extractor.py` + `media_extractor.py`
**Business:** site-level facts (how many pages, how deep, what was skipped/truncated) tell the reader how much of the site the audit actually saw — a trust boundary on every conclusion. Forms are the conversion surfaces EG-01 looks for.
**Tech:** `SiteExtractor.extract_site_evidence()` emits `CRAWL_COVERAGE` / `CRAWL_RESOURCE_SUMMARY` / `FAILED_URL_RECORD` / `SKIPPED_URL_RECORD` / `CRAWL_ERROR`; `MediaExtractor.extract_media_evidence()` emits `IMAGE_ITEM` and `FORM_ITEM` (action, method, input fields).

```mermaid
flowchart TD
    MF["CrawlManifest"] --> CV["CRAWL_COVERAGE(pages_discovered, pages_crawled, max_depth, truncated)"]
    MF --> FA["failed urls -> FAILED_URL_RECORD"]
    MF --> SK["skipped urls (robots) -> SKIPPED_URL_RECORD"]
    MF --> CE["fetch errors -> CRAWL_ERROR"]
    H["page HTML"] --> IM["images -> IMAGE_ITEM"]
    H --> FM["form action/method/inputs -> FORM_ITEM"]
    CV & FA & SK & CE & IM & FM --> E["coverage + interaction evidence"]
```

**Parent:** [src README](../README.md).
