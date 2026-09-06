# Architecture Decision Records (ADRs)

This document logs significant architectural decisions made during the design and development of the **Brand AI Readiness Audit** system.

---

## ADR-001: Evidence-First Architecture

### Context
Auditing a brand's website for AI readiness requires analyzing both deterministic technical criteria (e.g., `robots.txt` rules, Schema validation syntax) and qualitative content nuances (e.g., claim ambiguity, value proposition clarity). Relying solely on LLMs to browse the web or synthesize findings without structured evidence collection creates severe risks: models can hallucinate page elements, misjudge raw header configurations, or generate un-anchored observations that cannot be verified or reproduced by engineering teams.

### Decision
All deterministic extraction must execute first to populate an immutable **Evidence Store**. LLM reasoning components are strictly constrained to inspect collected evidence artifacts (DOM trees, header dumps, JSON-LD schemas, text blocks, AI query responses) rather than browsing live web pages directly. Every audit finding must be linked to explicit Evidence IDs.

### Consequences & Implementation Rules
1. Every audit sub-skill separates its execution into **Evidence Extraction** (deterministic) and **Evidence Analysis** (deterministic + LLM).
2. The Evidence Store holds immutable raw artifacts with unique IDs (`EVID-DOM-RAW`, `EVID-SCHEMA-JSONLD`, `EVID-AI-VISIBILITY`, etc.).
3. The Evidence Validation Engine purges any finding lacking verifiable Evidence IDs.
4. Audit results are 100% explainable, reproducible, and debuggable.

### Status
**Accepted**

---

## ADR-002: URL-Only Input & Automated Context Derivation

### Context
Legacy audit systems often require extensive user configuration, such as brand profile inputs (`brand_domain_context`, `canonical_brand_profile`, competitor lists, target keywords, industry taxonomy). In practical real-world usage and hackathon benchmarking, requiring manual inputs creates significant user friction and biases the audit with subjective brand claims.

### Decision
The system must accept **strictly a website URL as input** (`target_url`). All contextual understanding—including brand name, legal entity identity, core products/services, target audience, value propositions, and candidate discovery queries—must be derived automatically through multi-page DOM extraction, structured data parsing, and automated context synthesis.

### Consequences & Implementation Rules
1. Sub-skills (`fact-quality-audit`, `entity-identity-audit`, `engagement-audit`) must not declare mandatory user-supplied context parameters.
2. The system implements an **Automated Context Discovery Engine** that extracts brand identity from `<title>`, `Organization` schema, hero sections, About/Contact pages, and footer disclosures.
3. Test queries for AI visibility testing are generated dynamically from derived site context.

### Status
**Accepted**

---

## ADR-003: Two-Dimensional Audit Framework (Off-Site Discoverability & On-Site Engagement)

### Context
Initial scaffolding conflated multiple audit concerns or focused disproportionately on technical crawler directives and `/llms.txt`. In reality, a brand's AI readiness is determined by two distinct dimensions:
1. Whether search engines and AI discovery systems can find, crawl, index, understand, retrieve, and cite the brand (Off-site Discoverability).
2. Whether human visitors and autonomous AI agents can clearly understand offerings, navigate, trust, engage, and convert once on the website (On-site Engagement).

### Decision
Structure the audit framework around exactly **two primary dimensions**, each evaluated on an independent 0–100 normalized score:
- **Dimension A: Off-site Discoverability** (On-page SEO, Technical SEO, Off-page Authority, AI/GEO Discoverability, Machine Readability & Entity, Freshness & Corroboration).
- **Dimension B: On-site Engagement** (First-Visit Clarity, Content Engagement, Navigation & Findability, CTA & User Journey, Performance & Stability, Mobile UX, Trust & Credibility, Accessibility, AI-Agent Interaction Readiness).

### Consequences & Implementation Rules
1. The scoring engine calculates separate scores for Dimension A and Dimension B, combining them into an Overall Brand AI Readiness Index (50/50 weighting).
2. Reporting deliverables display sub-pillar breakdowns for both dimensions.

### Status
**Accepted**

---

## ADR-004: Separation of Structural AI Readiness from Observed AI Visibility

### Context
A website may be technically accessible to AI crawlers (valid `robots.txt`, SSR HTML, clean JSON-LD) but still remain completely invisible or mischaracterized in real-world generative search responses (ChatGPT, Perplexity, Gemini). Conversely, an unoptimized site might still be cited due to high external domain authority. Conflating technical crawler checks with real-world AI visibility produces misleading audits.

### Decision
Explicitly separate **Structural AI Readiness** from **Observed AI Visibility**:
1. **Structural AI Readiness**: Evaluates technical permissions (`robots.txt` AI bot directives), server-side rendering, schema markup completeness, and `/llms.txt` presence.
2. **Observed AI Visibility**: Empirically queries AI search engines with derived branded and categorical queries, capturing actual brand mention rates, citation link attributions, prominence ranking, and answer accuracy.

### Consequences & Implementation Rules
1. The AI / GEO sub-pillar allocates 50% weight to Structural checks and 50% weight to Observed AI Visibility test records.
2. Every empirical test preserves a complete evidence tuple: `{ query, ai_system, raw_response, brand_mentioned, domain_cited, prominence_rank, factual_accuracy_score, evidence_ids }`.

### Status
**Accepted**

---

## ADR-005: Inferred On-Site Engagement vs. Fabricated Behavioral Analytics

### Context
Because the system operates strictly on a URL-only input constraint, private web analytics (e.g., Google Analytics bounce rates, session durations, conversion funnels, returning visitor ratios) cannot be accessed. Simulating or estimating behavioral analytics without real data leads to fabricated metrics that undermine audit credibility.

### Decision
The system **must never fabricate behavioral analytics**. On-site Engagement must be inferred strictly from observable technical, structural, visual, and UX characteristics (above-the-fold clarity, heading scannability, click depth to core pages, CTA contrast and simplicity, Core Web Vitals, mobile viewport layout, trust disclosures, and WCAG accessibility signals).

### Consequences & Implementation Rules
1. Reports must state qualitative, evidence-backed findings (e.g., "The primary CTA button has low contrast and requires 4 navigation clicks to reach from the pricing page") rather than fabricated claims (e.g., "Bounce rate is 68%").
2. Scoring rubrics for on-site engagement rely exclusively on deterministically observable DOM, visual layout, and performance metrics.

### Status
**Accepted**

---

## ADR-006: Audit-Derived Scoring, Missing Evidence Protocol & False-Positive Mitigation

### Context
Audit systems often suffer from two major flaws:
1. Making misleading claims (e.g., "This is your official Google SEO score").
2. Penalizing websites unfairly when external metrics cannot be retrieved, or failing to account for valid edge cases (parent/subsidiary brands, rebrand transitions, intentional staging bot blocks, evergreen content).

### Decision
1. **Audit-Derived Calibration**: Scores are explicitly framed as 0–100 *Audit-Derived Readiness Indexes* based on transparent, calibrated heuristics and empirical tests.
2. **Missing Evidence Protocol**: If external data (such as third-party backlink authority) is unavailable via public observation, it is recorded as `Unknown / Unavailable` rather than `Failed`, and its scoring weight is dynamically redistributed to avoid artificial penalties.
3. **False-Positive Mitigation**: Evaluators must incorporate explicit handling for:
   - Parent company vs. subsidiary entity naming differences.
   - Rebranding transition phases with legacy domain redirects.
   - Intentional bot restrictions (e.g., restricting scraper bots while permitting search bots).
   - Evergreen foundational content that requires no artificial `dateModified` churn.
   - Early-stage startups with minimal pre-existing external Knowledge Graph presence.

### Consequences & Implementation Rules
1. All score outputs include confidence indicators and data availability flags.
2. Severity rubrics distinguish high-risk blockers (e.g., broken pricing CTA or total AI crawler block) from acceptable context-specific patterns.

### Status
**Accepted**
