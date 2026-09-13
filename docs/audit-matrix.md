# Brand AI Readiness Audit Matrix

This matrix defines the audit categories, evaluation signals, required evidence, severity classification, scoring methodologies, and false-positive considerations.

---

## Evaluation Flow Model

Every skill check follows an explicit 4-stage analytical transformation chain:

```
Observation / Evidence
 → Finding
 → Severity
 → Recommendation
```

1. **Observation / Evidence**: Structured, un-summarized raw ground-truth collected from HTTP headers, DOM snapshots, JSON-LD, or `robots.txt` (e.g. `source_url`, `evidence_type`, `observed`, `location`).
2. **Finding**: Evaluated result of a specific skill check (`check_id`, `title`, `status`, `description`), directly linked to its supporting evidence items.
3. **Severity**: Standardized risk classification (`critical`, `high`, `medium`, `low`, `info`) reflecting the impact on AI models and agents.
4. **Recommendation**: Actionable remediation guidance providing clear steps for engineering or content teams to resolve identified issues.

---

## 1. Crawl & Render Accessibility

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | Crawl & Render Accessibility |
| **Signal** | AI Bot Disallow Rules (`robots.txt`), HTTP Header restrictions (`X-Robots-Tag`), Client-Side Rendering (CSR) blocking, Sitemap accessibility. |
| **Evidence** | `robots.txt` parse logs, HTTP response headers, DOM diff (Pre-JS vs Post-JS rendered HTML), Sitemap XML HTTP status. |
| **Severity** | **Critical** (if AI bots completely blocked) to **Medium** (if JS rendering delays data extraction). |
| **Scoring** | *Placeholder* (e.g., 0–100 sub-score based on percentage of unblocked core pages and SSR availability). |
| **False-Positive Considerations** | Intentional staging/testing disallows, geo-fencing, anti-scraping rate limits misidentified as bot blocks. |

---

## 2. Structured Data & Semantic Markup

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | Structured Data & Semantic Markup |
| **Signal** | Schema.org JSON-LD presence, Microdata syntax validity, OpenGraph completeness, semantic HTML tags (`<article>`, `<header>`, `<table>`). |
| **Evidence** | Extracted JSON-LD payloads, Schema validator syntax error logs, DOM element tree analysis. |
| **Severity** | **High** (missing Organization / Product schemas) to **Low** (missing optional schema fields). |
| **Scoring** | *Placeholder* (e.g., Weighted score based on essential schema presence and validation errors). |
| **False-Positive Considerations** | Duplicate schemas across head/body, valid custom extensions not recognized by generic validators. |

---

## 3. Factual & Content Quality

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | Factual & Content Quality |
| **Signal** | Claim clarity, statistical precision, un-ambiguous phrasing, absence of conflicting assertions, hallucination-vulnerable text blocks. |
| **Evidence** | Extracted text propositions, ambiguity flags, contradictory statement pairs, readability indices. |
| **Severity** | **High** (conflicting pricing or core product specs) to **Medium** (vague marketing jargon). |
| **Scoring** | *Placeholder* (e.g., Percentage of verified non-ambiguous claims across sampled landing pages). |
| **False-Positive Considerations** | Context-dependent terminology, figurative marketing language, regional product variance. |

---

## 4. Content Freshness

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | Content Freshness |
| **Signal** | Explicit `dateModified` / `datePublished` metadata, sitemap `<lastmod>` tags, HTTP `Last-Modified` headers, visible date stamps. |
| **Evidence** | HTTP response headers, JSON-LD date properties, DOM timestamp selectors, sitemap entry timestamps. |
| **Severity** | **Medium** (stale content over 12 months old) to **Low** (missing last modified header on static pages). |
| **Scoring** | *Placeholder* (e.g., Decay function applied to page age relative to industry update norms). |
| **False-Positive Considerations** | Dynamic copyright year updates in footers misidentified as content revisions, evergreen content marked stale. |

---

## 5. External Corroboration

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | External Corroboration |
| **Signal** | Citation by third-party authoritative sources, Wikipedia/Wikidata entity links, cross-domain brand mentions, press release alignment. |
| **Evidence** | External link graph data, search engine index snippets, Wikipedia backlink records, cross-site reference matches. |
| **Severity** | **High** (un-corroborated major brand claims) to **Medium** (missing third-party citations for sub-products). |
| **Scoring** | *Placeholder* (e.g., Ratio of corroborated core brand assertions to total assertions). |
| **False-Positive Considerations** | Sub-brands or newly launched products with minimal external index history, proprietary trade names. |

---

## 6. Entity Identity & Consistency

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | Entity Identity & Consistency |
| **Signal** | Brand Name, Address, Phone (NAP) uniformity, canonical Organization schema `sameAs` links, Knowledge Graph ID consistency. |
| **Evidence** | `sameAs` URL arrays, Wikidata entity IDs, cross-page NAP text matches, logo asset URL consistency. |
| **Severity** | **High** (conflicting legal entity names or missing canonical links) to **Medium** (minor address format differences). |
| **Scoring** | *Placeholder* (e.g., Consistency ratio across canonical site pages and social profiles). |
| **False-Positive Considerations** | Parent company vs subsidiary name usage, recent brand renames in transition phase. |

---

## 7. AI Discoverability & GEO Readiness

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | AI Discoverability & GEO Readiness |
| **Signal** | Direct answerability for high-intent queries, structured FAQ presence, tabular spec data, AI crawler indexability. |
| **Evidence** | Q&A DOM blocks, HTML table structures, text snippet conciseness ratings, LLM extraction success rate. |
| **Severity** | **High** (product specs locked in images or un-parsable PDFs) to **Low** (sub-optimal heading hierarchy). |
| **Scoring** | *Placeholder* (e.g., GEO composite score evaluating answer density and direct extraction ease). |
| **False-Positive Considerations** | Highly visual products requiring graphical presentation, gated whitepapers. |

---

## 8. On-Site Visitor Engagement & Conversion (EG-01..04)

| Attribute | Definition / Specification |
| :--- | :--- |
| **Category** | On-Site Visitor Engagement & Conversion |
| **Signal** | Above-the-fold clarity (who/what/next), navigation coverage vs claimed offerings, breadcrumb presence on interior pages, real conversion CTAs vs "Learn More" loops. |
| **Evidence** | H1/heading text, above-fold paragraph content, nav anchor inventory vs page claims, breadcrumb trail DOM elements, CTA anchor text and href targets. |
| **Severity** | **High** (no clear who/what/next on content-rich landing page) to **Medium** (missing breadcrumbs on deep interior pages, nav/offerings mismatch, circular Learn More loops with no signup/buy/contact/demo CTA). |
| **Scoring** | *Placeholder* (e.g., Orientation score combining clarity, navigation coverage, breadcrumb depth coverage, and CTA actionability). |
| **False-Positive Considerations** | JS shells with <80 words are owned by Crawl & Render (EG-01 does not double-flag); single-page sites legitimately lacking breadcrumbs; legal/privacy pages excluded from CTA analysis. |

**Scope note:** This skill evaluates *human visitor* orientation and conversion only. It deliberately does NOT flag missing `/llms.txt`, `/openapi.json`, chat widgets, or conversational endpoints — those are out of the official Round 3 on-site engagement scope.
