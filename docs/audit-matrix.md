# Brand AI Readiness Audit Matrix

This matrix defines the complete audit taxonomy across the two primary dimensions: **Off-site Discoverability** and **On-site Engagement**. It specifies the evaluation signals, required evidence artifacts, severity classifications, scoring methodologies, and false-positive considerations for every sub-pillar.

---

## Evaluation Flow Model

Every skill check follows an explicit 4-stage analytical transformation chain:

```
Observation / Evidence
 ➔ Finding
 ➔ Severity
 ➔ Recommendation
```

1. **Observation / Evidence**: Structured, un-summarized raw ground-truth collected from HTTP headers, DOM snapshots, JSON-LD, or `robots.txt` (e.g. `source_url`, `evidence_type`, `observed`, `location`).
2. **Finding**: Evaluated result of a specific skill check (`check_id`, `title`, `status`, `description`), directly linked to its supporting evidence items.
3. **Severity**: Standardized risk classification (`critical`, `high`, `medium`, `low`, `info`) reflecting the impact on search engines, AI models, and users.
4. **Recommendation**: Actionable remediation guidance providing clear steps for engineering or content teams to resolve identified issues.

---

## Architecture Overview & Audit Dimensions

The audit evaluates brand digital presence along two primary axes:

```
                          Overall Brand AI Readiness (0–100)
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
Dimension A: Off-site Discoverability                     Dimension B: On-site Engagement
(Can search engines & AI systems crawl,                   (Can human visitors & AI agents understand,
 index, understand, retrieve, cite & trust?)               navigate, trust, engage & convert on-site?)
```

---

# DIMENSION A: OFF-SITE DISCOVERABILITY

---

## A.1 On-Page SEO & Content Quality

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / On-Page SEO & Content Quality |
| **Description** | Evaluates whether individual page content is original, comprehensive, well-structured, and optimized for search engine indexing and LLM semantic retrieval. |
| **Evaluation Signals** | • Content depth, completeness, and topical relevance<br>• Value-to-noise ratio; detection of thin, boilerplate, or duplicate content<br>• Title tags: presence, uniqueness, length (50–60 chars), brand alignment, keyword relevance<br>• Meta descriptions: presence, uniqueness, length (120–160 chars), call-to-action intent<br>• Heading hierarchy: single `<h1>`, logical `<h2>`–`<h6>` structure without skipping levels<br>• URL structure: clean, descriptive, readable slug hierarchy, absence of excessive parameters<br>• Image accessibility: presence of descriptive, contextual `alt` attributes<br>• Internal link architecture: descriptive anchor text, absence of broken internal links, orphan page detection |
| **Evidence Required** | • DOM extraction: `<title>`, `<meta name="description">`, heading tree hierarchy (`<h1>`–`<h6>`)<br>• Text-to-code ratio and word counts of main content containers vs boilerplate<br>• Image element audit table (`src`, `alt`, bounding box visibility)<br>• Link graph: internal URL crawl edges, HTTP status codes, anchor text mappings |
| **Severity** | • **Critical**: Missing or duplicate `<h1>` on key landing pages; broken core navigation links; site-wide missing title tags<br>• **High**: Thin or duplicated content across core pages; generic title tags; missing meta descriptions<br>• **Medium**: Sub-optimal heading nesting (e.g., `<h3>` before `<h2>`); missing alt text on informational images<br>• **Low**: Minor title/description character count overflow; non-descriptive anchor text ("click here") |
| **Scoring Methodology** | 0–100 score calculated via weighted rubric:<br>• Title & Meta Quality: 25%<br>• Content Depth & Originality: 30%<br>• Heading & Document Hierarchy: 20%<br>• Internal Linking & Architecture: 15%<br>• Image Alt Text Coverage: 10% |
| **False-Positive Considerations** | Intentional utility/login pages with minimal copy; single-page apps (SPAs) with dynamic titles rendered post-hydration; decorative images marked with `alt=""` or `aria-hidden="true"` (which is correct behavior). |

---

## A.2 Technical SEO & Crawlability

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / Technical SEO & Crawlability |
| **Description** | Assesses fundamental technical infrastructure ensuring search bots and crawlers can fetch, render, and index pages securely and efficiently. |
| **Evaluation Signals** | • Robots configuration: `robots.txt` availability, validity, and non-blocking crawl directives<br>• XML Sitemaps: `sitemap.xml` presence, declared in `robots.txt`, valid XML schema, HTTP status of URLs, coverage of canonical pages<br>• Indexing controls: `robots` meta tags, `X-Robots-Tag` headers, `noindex`/`nofollow` directives<br>• Canonicalization: explicit `<link rel="canonical">` on every indexable page, self-referential canonicals, cross-domain canonicals<br>• HTTP response status & redirects: 200 OK statuses, clean 301 redirects, absence of redirect loops/chains, proper 404/410 handling<br>• Security & Protocol: HTTPS enforcement, SSL/TLS certificate validity, mixed content absence, security headers (`HSTS`, `Content-Security-Policy`)<br>• Performance / Core Web Vitals (Observable): Page load speed, LCP (Largest Contentful Paint), INP (Interaction to Next Paint), CLS (Cumulative Layout Shift), resource weight, JavaScript execution cost |
| **Evidence Required** | • Raw `robots.txt` payload and parsed directive AST<br>• XML sitemap fetch response, URL list, and status code verification logs<br>• HTTP response header dumps (status code, `X-Robots-Tag`, `Strict-Transport-Security`)<br>• HTML `<head>` canonical tag extraction<br>• Redirect chain logs (trace of intermediate URLs and HTTP status codes)<br>• Browser performance metrics: LCP, CLS, TTFB, DOMContentLoaded, Total Blocking Time (TBT) |
| **Severity** | • **Critical**: `robots.txt` blocking search crawlers from root; invalid SSL certificate; recursive redirect loops; `noindex` tag on core landing page<br>• **High**: Missing or inaccessible XML sitemap; missing canonical tags leading to duplicate URL indexing; mixed HTTP/HTTPS assets; LCP > 4.0s<br>• **Medium**: Redirect chains (>2 hops); slow TTFB (>1.5s); missing HSTS headers<br>• **Low**: Non-critical sitemap URL 404s; minor layout shifts (CLS 0.1–0.25) |
| **Scoring Methodology** | 0–100 score calculated via weighted rubric:<br>• Crawl Accessibility & `robots.txt`: 25%<br>• Indexing Directives & Canonicalization: 25%<br>• Sitemap Health & Coverage: 20%<br>• HTTPS & Security Transport: 15%<br>• Core Performance & Response Codes: 15% |
| **False-Positive Considerations** | Intentional staging environment blocks (`noindex` on preview subdomains); geo-restricted IP responses; rate-limiting anti-DDoS firewalls (Cloudflare) misidentified as crawler failures. |

---

## A.3 Off-Page Authority & Reputation

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / Off-Page Authority & Reputation |
| **Description** | Evaluates external signals of brand credibility, citations, backlinks, and brand reputation across the web. |
| **Evaluation Signals** | • Backlink profile quality: estimated referring domains, domain authority tier (where publicly observable)<br>• Topical authority & link diversity: anchor text distribution, relevant industry backlinks<br>• Unlinked brand mentions in reputable industry publications<br>• Third-party reviews and ratings (Trustpilot, G2, Capterra, Google Business)<br>• Local citations and directory consistency (for local businesses) |
| **Evidence Required** | • Public search engine result snippets and citation records<br>• Verified third-party review platform profiles and aggregate rating badges<br>• Cross-domain reference links and public press release listings<br>• **Missing Evidence Rule**: If external backlink or authority metrics cannot be reliably retrieved via public observation, report **Unknown / Unavailable** instead of fabricating numbers. |
| **Severity** | • **Critical**: Severe unaddressed public reputation crisis or widespread scam flags documented on authoritative platforms<br>• **High**: Zero external domain citations for an established enterprise brand<br>• **Medium**: Outdated or inconsistent profiles on major review/directory platforms<br>• **Low**: Minor anchor text concentration |
| **Scoring Methodology** | 0–100 score based on available observable signals. If authoritative data is unavailable, this sub-pillar is scored as **Unknown / Neutral** and excluded from penalty calculations to prevent artificial score depression. |
| **False-Positive Considerations** | Newly launched startups with low initial backlink footprints; niche B2B enterprises that do not use consumer review platforms; proprietary brand acronyms. |

---

## A.4 AI / GEO Discoverability (Structural & Observed)

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / AI & Generative Engine Optimization (GEO) |
| **Description** | Measures both technical accessibility for AI crawlers (Structural) and real-world answer generation/citation performance (Observed Visibility) across AI discovery engines. |
| **Evaluation Signals** | **1. Structural AI Accessibility:**<br>• Explicit AI User-Agent directives in `robots.txt` (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, `Amazonbot`, `Bytespider`)<br>• Server-side rendering (SSR) vs. Client-side rendering (CSR) parity (ensuring content is visible without complex JavaScript execution)<br>• Machine-parsable content formats (tabular data, structured definitions, concise extractable answers)<br>• Availability of `/llms.txt` and `/llms-full.txt` files providing markdown entity summaries<br><br>**2. Observed AI Visibility (Empirical Testing):**<br>• Brand mention rate in AI responses for branded and categorical queries<br>• Citation / Source attribution rate (brand domain cited as authoritative reference)<br>• Answer correctness (factual accuracy of AI summaries regarding offerings, pricing, features)<br>• Prominence & position (brand cited as top recommendation vs buried mention)<br>• Entity accuracy (correct brand identification vs conflation with namesakes) |
| **Evidence Required** | • Parsed `robots.txt` rules per AI bot User-Agent<br>• Pre-JS raw HTML vs. Post-JS rendered DOM diff analysis<br>• `/llms.txt` HTTP response body and markdown validation<br>• **AI Visibility Test Records**: Stored tuples of `{ query, ai_system, raw_response, brand_mentioned, domain_cited, prominence_rank, factual_accuracy_score, evidence_ids }` |
| **Severity** | • **Critical**: Unintended blanket block of all AI crawlers (`User-agent: * Disallow: /` or blocking `GPTBot`/`ClaudeBot`/`PerplexityBot` without strategic rationale); severe AI hallucination attributing fraudulent services to brand<br>• **High**: Essential product specs/pricing locked behind client-side JS invisible to LLM crawlers; AI engines consistently cite competitors for direct brand queries<br>• **Medium**: Missing `/llms.txt` file; lack of concise extractable summary blocks for high-intent queries<br>• **Low**: Minor non-standard formatting in markdown exports |
| **Scoring Methodology** | 0–100 composite score split between:<br>• Structural AI Readiness (50%): AI crawler permissions (25%), SSR/JS content extraction (15%), `/llms.txt` & direct answer structuring (10%)<br>• Observed AI Visibility (50%): Branded query recall & accuracy (25%), Categorical query discovery & citation rate (25%) |
| **False-Positive Considerations** | Intentional IP-protection blocking of training bots (e.g., blocking `Bytespider` while permitting search bots like `PerplexityBot`); newly launched brands with minimal pre-training corpus presence (must evaluate real-time search LLMs separately from frozen base models). |

---

## A.5 Machine Readability & Entity Understanding

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / Machine Readability & Entity Understanding |
| **Description** | Assesses Schema.org structured data, semantic HTML markup, OpenGraph tags, and entity disambiguation signals. |
| **Evaluation Signals** | • Schema.org JSON-LD presence, completeness, and syntax validity<br>• Core schema type coverage: `Organization`, `WebSite`, `Product`, `SoftwareApplication`, `Article`, `FAQPage`, `LocalBusiness`<br>• Entity linkage: `sameAs` array linking to authoritative profiles (Wikidata, Wikipedia, LinkedIn, Twitter/X, Crunchbase, GitHub)<br>• Canonical entity signals: unambiguous legal entity name, official logo URL, primary domain, contact points<br>• OpenGraph & Twitter Card completeness (`og:title`, `og:description`, `og:image`, `og:url`)<br>• Semantic HTML structure: `<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`, `<table>`, `<dl>` |
| **Evidence Required** | • Extracted JSON-LD and Microdata blocks from DOM<br>• Schema.org validator error/warning logs<br>• Parsed OpenGraph `<meta>` tag dictionary<br>• Semantic tag distribution matrix across core templates |
| **Severity** | **Critical**: Malformed JSON-LD syntax crashing parsers; conflicting entity definitions (`Organization` name mismatch between pages)<br>• **High**: Missing `Organization` or `Product` schemas on core commercial pages; empty or broken `sameAs` links<br>• **Medium**: Missing OpenGraph image tags; nested schema reference errors<br>• **Low**: Omission of optional Schema.org properties (e.g., `priceRange` on generic organization) |
| **Scoring Methodology** | 0–100 score calculated via:<br>• Core Entity Schema (`Organization`/`sameAs`): 30%<br>• Page-Specific Schema (`Product`/`Article`/`FAQPage`): 30%<br>• Syntax Validity & Error Absence: 20%<br>• OpenGraph & Social Metadata: 10%<br>• Semantic HTML Element Usage: 10% |
| **False-Positive Considerations** | Custom Schema extensions not registered in core Schema.org namespace; multi-brand parent companies with separate operating entity schemas. |

---

## A.6 Freshness & Corroboration

| Attribute | Specification |
| :--- | :--- |
| **Category** | Off-site Discoverability / Freshness & Corroboration |
| **Description** | Validates temporal signals, content update cadences, and cross-source factual corroboration to ensure AI models trust brand data as timely and accurate. |
| **Evaluation Signals** | • Explicit temporal metadata: `datePublished` and `dateModified` in Schema JSON-LD<br>• HTTP header timestamps: `Last-Modified`, `ETag`, `Cache-Control`<br>• XML sitemap `<lastmod>` accuracy and consistency with page headers<br>• Visible on-page publication/update timestamps<br>• Stale page detection: core pricing, policy, or feature pages unchanged for >18 months without confirmation<br>• Cross-source corroboration: alignment of core facts (pricing, leadership, headquarters) across website, schema, and external knowledge graphs |
| **Evidence Required** | • Extracted date properties from JSON-LD, meta tags, and DOM selectors<br>• HTTP response header timestamp logs<br>• Sitemap `<lastmod>` timestamps compared against document headers<br>• Fact proposition verification records across external knowledge bases |
| **Severity** | • **Critical**: Severe contradiction between on-page pricing/terms and external legal disclosures; `dateModified` spoofing (dates in future)<br>• **High**: Stale core product pages (>2 years old) causing AI engines to cite obsolete product lines<br>• **Medium**: Missing `dateModified` on technical/documentation articles; sitemap `<lastmod>` missing or identical for all pages<br>• **Low**: Minor timestamp formatting inconsistencies (ISO-8601 vs RFC-2822) |
| **Scoring Methodology** | 0–100 score calculated via:<br>• Timestamp Metadata Completeness: 35%<br>• Sitemap `<lastmod>` & Header Parity: 25%<br>• Content Freshness & Update Cadence: 20%<br>• External Fact Corroboration: 20% |
| **False-Positive Considerations** | Evergreen foundational content (e.g., philosophy, core mission) that requires no frequent updates; footer copyright year auto-increments misidentified as article content revisions. |

---

# DIMENSION B: ON-SITE ENGAGEMENT

---

## B.1 First-Visit Clarity

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / First-Visit Clarity |
| **Description** | Evaluates whether a new visitor (human or AI agent) can immediately understand the brand's core value proposition, target audience, and primary action within the above-the-fold viewport. |
| **Evaluation Signals** | • Above-the-fold value proposition: clear headline (`<h1>`), subheadline, and explanatory copy<br>• Core offering clarity: immediate understanding of what product/service is provided and what problem it solves<br>• Target audience clarity: self-selection cues for intended users/customers<br>• Visual relevance: hero imagery or product previews supporting the core message<br>• Primary next action: prominent, unambiguous above-the-fold call to action (CTA) |
| **Evidence Required** | • Above-the-fold DOM snapshot and layout bounding boxes<br>• Extracted hero headline text, sub-text, and button labels<br>• LLM proposition analysis evaluating clarity vs vague jargon score |
| **Severity** | • **Critical**: Homepage hero contains zero explanatory text (only abstract imagery or cryptic tagline like "Dream Tomorrow")<br>• **High**: Value proposition buried far below the fold; primary offering completely ambiguous to a first-time reader<br>• **Medium**: Jargon-heavy copy requiring deep domain expertise to parse<br>• **Low**: Minor typography size imbalance between headline and subheadline |
| **Scoring Methodology** | 0–100 score derived from:<br>• Value Proposition Clarity & Precision: 40%<br>• Above-the-Fold Primary CTA Visibility: 30%<br>• Problem/Solution Definition: 20%<br>• Supporting Context & Visual Relevance: 10% |
| **False-Positive Considerations** | Universally recognized consumer mega-brands (e.g., Apple, Nike) whose brand recognition allows minimalist hero designs; localized international landing pages. |

---

## B.2 Content Engagement & Scannability

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Content Engagement & Scannability |
| **Description** | Assesses how readable, structured, visually supported, and scannable content is for human readers and parsing agents. |
| **Evaluation Signals** | • Reading ease: Flesch-Kincaid / Gunning-Fog readability scores appropriate for target audience<br>• Scannability: use of concise paragraphs (2–4 sentences), bulleted/numbered lists, callout boxes<br>• Heading utility: descriptive section headers allowing fast visual scanning<br>• Information density: absence of dense, unbroken walls of text<br>• Supporting media: informative diagrams, charts, product screenshots, or video explainers |
| **Evidence Required** | • Content block length distributions (word count per paragraph and section)<br>• List element (`<ul>`, `<ol>`) and data table counts<br>• Readability index computations on extracted main body copy<br>• Media element mapping within content containers |
| **Severity** | • **High**: Long, unbroken walls of text (>400 words per block) with no sub-headings or lists on core informational pages<br>• **Medium**: Readability grade level excessively complex (e.g., Grade 16+ on general consumer product); poor contrast or dense layout<br>• **Low**: Occasional oversized paragraphs; missing bullet points in feature lists |
| **Scoring Methodology** | 0–100 score derived from:<br>• Heading Structure & Section Segmentation: 30%<br>• Paragraph Length & White Space Distribution: 25%<br>• Readability & Language Clarity: 25%<br>• Lists, Tables & Visual Explanations: 20% |
| **False-Positive Considerations** | Legal documents (Terms of Service, Privacy Policies) and scientific/academic publications where dense text is standard. |

---

## B.3 Navigation & Findability

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Navigation & Findability |
| **Description** | Measures how intuitively and efficiently visitors and bots can traverse the information architecture and find key resources. |
| **Evaluation Signals** | • Header navigation: concise, logical menu hierarchy with clear descriptive labels<br>• Footer navigation: comprehensive categorization of company, product, resources, legal, and contact links<br>• Key page discoverability: Pricing, Docs/Help, Contact, About, and Product pages accessible within <= 2 clicks from root<br>• Breadcrumbs: structured breadcrumb navigation on deep content/category pages<br>• Internal search: search input availability, clear placeholder, functional query parameters<br>• Dead-end / Orphan prevention: all pages provide logical next pathways; no disconnected leaf pages |
| **Evidence Required** | • Header `<nav>` and footer `<footer>` link trees<br>• Site crawl depth map (click distance from homepage to key entity pages)<br>• Breadcrumb DOM and `BreadcrumbList` schema extraction<br>• Search form DOM attributes and query handler inspection |
| **Severity** | • **Critical**: Broken main navigation menu; key commercial pages (Pricing, Contact) unreachable via links<br>• **High**: Key resources buried >4 clicks deep; absence of footer or header navigation on key sub-pages; dead-end pages<br>• **Medium**: Missing breadcrumbs on deep documentation/product catalogs; non-descriptive nav labels ("Stuff", "More")<br>• **Low**: Redundant navigation links; minor mobile menu tap delay |
| **Scoring Methodology** | 0–100 score calculated via:<br>• Key Page Discoverability (Pricing, About, Contact, Docs): 35%<br>• Header & Footer Navigation Structure: 30%<br>• Crawl Depth & Architecture Hierarchy: 20%<br>• Breadcrumbs & Internal Search Availability: 15% |
| **False-Positive Considerations** | Single-product micro-sites with minimal page hierarchy; gated web apps that intentionally conceal public navigation behind authentication. |

---

## B.4 CTA & User Journey

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / CTA & User Journey |
| **Description** | Evaluates the clarity, placement, consistency, and friction level of conversion pathways across the website. |
| **Evaluation Signals** | • Primary CTA clarity: distinct, action-oriented button copy ("Start Free Trial", "Book a Demo", "View Pricing")<br>• Visual prominence: high color contrast, prominent button sizing, consistent styling<br>• Journey alignment: CTA aligns logically with page context and user intent<br>• Conversion friction: form simplicity, number of required fields, absence of premature barrier gating<br>• Competing CTA conflict: clear visual hierarchy between primary and secondary actions (e.g., solid vs outline buttons)<br>• Journey integrity: all CTA links resolve to functional destination URLs without 404s or broken flows |
| **Evidence Required** | • CTA button element registry (`id`, `href`, button text, computed CSS background/text contrast)<br>• Form element inspection (number of `<input>` fields, required attributes, submit handlers)<br>• Target link destination status code verification logs |
| **Severity** | • **Critical**: Primary CTA button broken (404 destination or dead JavaScript handler); high-intent page has zero CTA<br>• **High**: Extreme conversion friction (e.g., 15+ required fields for a simple demo request); conflicting primary CTAs creating choice paralysis<br>• **Medium**: Low contrast CTA buttons blending into background; vague action labels ("Click", "Submit")<br>• **Low**: Minor button alignment issues on small viewports |
| **Scoring Methodology** | 0–100 score derived from:<br>• Primary CTA Visibility & Action-Oriented Phrasing: 35%<br>• Conversion Pathway Integrity (no dead links): 30%<br>• Form Simplicity & Low Friction: 20%<br>• Primary vs Secondary Visual Hierarchy: 15% |
| **False-Positive Considerations** | Informational non-profit or research websites where the primary goal is knowledge dissemination rather than commercial conversion. |

---

## B.5 Performance & Interactive Stability

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Performance & Interactive Stability |
| **Description** | Measures technical responsiveness, layout stability, and friction-free user interaction on the frontend. |
| **Evaluation Signals** | • Load speed & TTFB: fast initial server response (<800ms)<br>• Largest Contentful Paint (LCP): hero content rendered in <= 2.5s<br>• Cumulative Layout Shift (CLS): stable visual rendering without unexpected shifts (score <= 0.1)<br>• Interaction to Next Paint (INP) / Total Blocking Time (TBT): snappy UI interactions without long JS thread blocking<br>• Resource optimization: compressed modern image formats (WebP/AVIF), minified CSS/JS<br>• Smooth loading states: skeleton screens, absence of layout jarring during font/image loading |
| **Evidence Required** | • Performance timing metrics (TTFB, FCP, LCP, CLS, TBT) captured during browser rendering<br>• Resource waterfall logs (total page weight, JavaScript payload size, image asset sizes)<br>• CSS layout shift audit records |
| **Severity** | • **Critical**: Severe page freeze (>5s main-thread lockup); page weight >20MB crashing mobile browsers<br>• **High**: LCP > 4.5s; CLS > 0.25 (content constantly shifting during tap attempts); unoptimized 10MB background video blocking interaction<br>• **Medium**: TTFB > 1.8s; uncompressed PNG/JPEG images; render-blocking CSS/JS files<br>• **Low**: Minor non-blocking resource delays; CLS between 0.1 and 0.15 |
| **Scoring Methodology** | 0–100 score aligned with Core Web Vitals thresholds:<br>• LCP Performance: 30%<br>• CLS Layout Stability: 25%<br>• INP / Main-Thread Blocking: 25%<br>• TTFB & Asset Optimization: 20% |
| **False-Positive Considerations** | Heavy 3D WebGL / interactive canvas applications where higher initial payload is expected and accepted by design. |

---

## B.6 Mobile UX & Responsiveness

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Mobile UX & Responsiveness |
| **Description** | Assesses responsiveness, touch ergonomics, and content parity across mobile viewports. |
| **Evaluation Signals** | • Viewport configuration: `<meta name="viewport" content="width=device-width, initial-scale=1">`<br>• Responsive layout: fluid grid/flexbox layouts, absence of horizontal page overflow/scrolling<br>• Touch target sizing: interactive buttons and links >= 48x48px with adequate spacing<br>• Typography readability: font sizes >= 16px for body copy without pinch-to-zoom required<br>• Mobile navigation: functional hamburger menu, sticky/accessible mobile header<br>• Content parity: essential desktop content, pricing, and features fully accessible on mobile viewports |
| **Evidence Required** | • Mobile viewport DOM snapshot (375px & 390px widths)<br>• Horizontal scroll width computation (`scrollWidth > clientWidth` check)<br>• Touch target bounding box audit records<br>• Mobile vs desktop DOM diff verification |
| **Severity** | • **Critical**: Missing viewport meta tag causing desktop layout zoom out on mobile; broken mobile navigation menu preventing access to pages<br>• **High**: Horizontal overflow forcing horizontal scroll; essential pricing/product details stripped from mobile version<br>• **Medium**: Tiny touch targets (<30px) causing mis-taps; body text <14px<br>• **Low**: Minor margin clipping on small Android devices |
| **Scoring Methodology** | 0–100 score calculated via:<br>• Viewport Configuration & Overflow Absence: 30%<br>• Touch Target Size & Ergonomics: 25%<br>• Mobile Navigation Usability: 25%<br>• Desktop/Mobile Content Parity: 20% |
| **False-Positive Considerations** | Data tables with intentional horizontal scroll containers (correct responsive table pattern); complex desktop-first CAD/IDE web software. |

---

## B.7 Trust, Credibility & Compliance

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Trust, Credibility & Compliance |
| **Description** | Evaluates explicit brand identity proof, transparency, legal compliance, and security assurance signals that establish visitor trust. |
| **Evaluation Signals** | • Company transparency: dedicated About Us, leadership/team details, physical address, business registration/legal entity name<br>• Direct contact channels: functional Contact page, email addresses, phone numbers, support channels<br>• Legal & Privacy compliance: accessible Privacy Policy, Terms of Service, Cookie notice/consent mechanism<br>• Commercial credibility: transparent pricing disclosures, refund/cancellation policies, SLA guarantees<br>• Social proof & testimonials: verifiable customer logos, client testimonials, case studies, industry certifications (SOC2, ISO, HIPAA)<br>• Security & payment trust: secure checkout badges, SSL security indicators |
| **Evidence Required** | • Legal policy URL verification and HTTP status checks (`/privacy`, `/terms`)<br>• Extracted contact information blocks (email regex, phone regex, physical address strings)<br>• Verified testimonial, certification, and case study DOM elements |
| **Severity** | • **Critical**: E-commerce/SaaS site with missing Privacy Policy and Terms of Service; completely hidden company identity with no contact info<br>• **High**: Hidden pricing or unexpected hidden fees; broken contact forms; deceptive trust badges (unverifiable fake seals)<br>• **Medium**: Missing physical office address or legal entity registration; generic "support@" email with no ticketing option<br>• **Low**: Minor formatting inconsistencies on team bio pages |
| **Scoring Methodology** | 0–100 score derived from:<br>• Privacy Policy, Terms & Legal Compliance: 30%<br>• Direct Contact Info & Address Transparency: 25%<br>• Transparent Pricing & Refund Policies: 25%<br>• Social Proof, Case Studies & Certifications: 20% |
| **False-Positive Considerations** | Early-stage pre-launch stealth startups with minimal public disclosures; open-source hobbyist projects with no commercial entity. |

---

## B.8 Accessibility (Observable Technical Signals)

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / Accessibility (a11y) |
| **Description** | Measures machine-observable WCAG 2.1 AA accessibility signals that ensure inclusive access for disabled users and assistive technologies. |
| **Evaluation Signals** | • Document language: `<html lang="...">` attribute defined and valid<br>• Form accessibility: explicit `<label>` elements associated with form inputs via `for`/`id`<br>• Heading semantics: logical hierarchy without skipped levels for screen readers<br>• Accessible names: all interactive elements (`<button>`, `<a>`, `<input>`) have accessible text or `aria-label`<br>• Visual contrast: observable text color vs background contrast meeting WCAG AA (>= 4.5:1 for normal text)<br>• Keyboard focus: observable focus indicators on interactive controls, absence of keyboard traps |
| **Evidence Required** | • Document HTML root attributes<br>• Form input-to-label association mapping table<br>• Interactive element accessible name registry<br>• Automated color contrast calculation logs for key text containers |
| **Severity** | • **Critical**: Unlabeled form inputs on checkout/login forms; total absence of keyboard focus accessibility<br>• **High**: Critical buttons lacking accessible names (`<button><svg></button>` without `aria-label`); low contrast text (<3:1)<br>• **Medium**: Missing `<html lang>` attribute; skipped heading levels; missing `alt` text on functional icons<br>• **Low**: Minor contrast deficit on non-essential footer links (4.2:1 vs 4.5:1) |
| **Scoring Methodology** | 0–100 score calculated via:<br>• Form Input Labels & Accessible Names: 35%<br>• Color Contrast Compliance: 25%<br>• Semantic Document Structure & Lang Attribute: 25%<br>• Focus Indicators & Keyboard Ergonomics: 15% |
| **False-Positive Considerations** | Complex canvas animations or custom SVG widgets using ARIA live regions that automated static scanners cannot fully interpret. |

---

## B.9 AI-Agent Interaction Readiness

| Attribute | Specification |
| :--- | :--- |
| **Category** | On-site Engagement / AI-Agent Interaction Readiness |
| **Description** | Assesses website capabilities that enable autonomous AI agents to search, retrieve machine-formatted documentation, and execute transactions programmatically. |
| **Evaluation Signals** | • Standard `/llms.txt` and `/llms-full.txt` presence and specification compliance<br>• Machine-readable API specs: discoverable OpenAPI (`/openapi.json`, `/.well-known/openapi.yaml`)<br>• Transparent internal search: predictable URL query structure (e.g., `/search?q=...`) that agents can query directly<br>• Conversational assistant integration: discoverable, standards-based assistant or search endpoint<br>• Machine-readable action manifests: standardized action schema for booking, purchasing, or querying inventory<br>• Predictable DOM data containers: clean `data-*` attributes and structured tables for programmatic extraction |
| **Evidence Required** | • HTTP GET response for `/llms.txt` and `/llms-full.txt`<br>• OpenAPI endpoint discovery logs and JSON spec validation<br>• Internal search form parameter analysis<br>• Data container attribute inspection |
| **Severity** | • **High**: Site actively prevents all agentic task completion via non-standard obfuscated search parameters; malformed `/llms.txt` providing invalid links<br>• **Medium**: Missing `/llms.txt` on a developer/API-centric platform; undocumented internal search endpoint<br>• **Low**: OpenAPI spec lacking operation descriptions; non-standard search query parameter key |
| **Scoring Methodology** | 0–100 score derived from:<br>• `/llms.txt` Availability & Specification Compliance: 40%<br>• Transparent Search Parameter Structure: 25%<br>• OpenAPI / Machine Endpoint Discoverability: 20%<br>• Structured Action Manifests & Data Selectors: 15% |
| **False-Positive Considerations** | Consumer editorial blogs or portfolio websites where developer API endpoints are not applicable; security-sensitive banking/medical portals. |

---

# Scoring Aggregation & Weighting Matrix

## Dimension Sub-Pillar Weights

```
DIMENSION A: OFF-SITE DISCOVERABILITY (100 pts)
├── A.1 On-Page SEO & Content Quality         (18%)
├── A.2 Technical SEO & Crawlability          (20%)
├── A.3 Off-Page Authority & Reputation       (12%)
├── A.4 AI / GEO Discoverability              (25%)
├── A.5 Machine Readability & Entity          (15%)
└── A.6 Freshness & Corroboration             (10%)

DIMENSION B: ON-SITE ENGAGEMENT (100 pts)
├── B.1 First-Visit Clarity                   (18%)
├── B.2 Content Engagement & Scannability     (12%)
├── B.3 Navigation & Findability              (14%)
├── B.4 CTA & User Journey                    (15%)
├── B.5 Performance & Interactive Stability   (12%)
├── B.6 Mobile UX & Responsiveness            (10%)
├── B.7 Trust, Credibility & Compliance       (8%)
├── B.8 Accessibility (Observable Signals)    (6%)
└── B.9 AI-Agent Interaction Readiness        (5%)
```

## Overall Brand AI Readiness Score Formula

$$\text{Overall Score} = (0.50 \times \text{Off-site Discoverability}) + (0.50 \times \text{On-site Engagement})$$

*Note: All scores are normalized between 0 and 100. If any metric is marked "Unknown / Unavailable" due to lack of public data (e.g., private backlink graphs or private analytics), its weight is dynamically redistributed across observable sub-pillars within the same category to prevent score skewing.*
