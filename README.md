# Brand AI Readiness Audit

> **Adobe University Hackathon 2026 — Round 3 Project**  
> An automated, evidence-first audit platform that evaluates a brand's digital presence for generative AI search engines, traditional search crawlers, human visitors, and autonomous AI agents using **URL-only input**.

---

## 🎯 Core Problem & Mission

As generative AI answer engines (ChatGPT Search, Perplexity AI, Google AI Overviews, Claude) transform how consumers discover information, brands face a fundamental question:

> **Given only a brand's website URL, how discoverable, understandable, trustworthy, and engaging is that brand for both AI/search systems and human visitors?**

Traditional SEO tools focus solely on legacy keyword rankings and backlink counts. The **Brand AI Readiness Audit** addresses the modern search paradigm across **two foundational dimensions**:

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

## ⚡ Key Architectural Principles

1. **URL-Only Input**: The user provides **only a website URL**. The system automatically derives all brand identity, core offerings, value propositions, and candidate test queries directly from website assets. No manual brand profiles, competitor lists, or analytics credentials are required.
2. **Structural AI Readiness + Observed AI Visibility**: We evaluate both technical crawler permissions (`robots.txt`, SSR/JS rendering, Schema.org, `/llms.txt`) and empirical answer generation (real-world AI mention rates, domain citation frequency, prominence rank, and factual answer accuracy).
3. **Inferred On-Site Engagement (No Fabricated Analytics)**: Because private analytics cannot be observed from a URL alone, engagement is inferred strictly from observable technical, structural, visual, and UX signals (above-the-fold clarity, heading scannability, CTA contrast/friction, Core Web Vitals, mobile ergonomics, trust disclosures, and WCAG accessibility).
4. **Evidence-First Grounding**: Deterministic tools extract raw artifacts (DOM snapshots, headers, schemas, text blocks, AI query tuples) into an **Immutable Evidence Store**. LLM reasoning operates exclusively on collected evidence, and 100% of reported findings cite verifiable Evidence IDs.
5. **Missing Evidence Protocol**: If external data (e.g., private backlink graphs) cannot be observed, it is recorded as `Unknown / Unavailable` rather than `Failed`, preventing artificial score penalties.

---

## 🏗️ System Architecture Flow

```
                                 [ Target Website URL ]
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              1. Automated Context Discovery           │
               │   (Derive Brand Entity, Offerings, and Test Queries)  │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              2. Crawl & Rendering Engine              │
               │   (Playwright Headless Browser, Raw HTML, Headers)    │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              3. Immutable Evidence Store              │
               │   (Raw DOMs, Rendered DOMs, JSON-LD, Text, Headers)   │
               └───────────────────────────┬───────────────────────────┘
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
┌─────────────────────────────────────────┐ ┌─────────────────────────────────────────┐
│     Dimension A: Off-site Discovery     │ │      Dimension B: On-site Engagement    │
│  ├── A.1 On-Page SEO & Content Quality  │ │  ├── B.1 First-Visit Clarity            │
│  ├── A.2 Technical SEO & Crawlability   │ │  ├── B.2 Content Scannability           │
│  ├── A.3 Off-Page Authority (Observable)│ │  ├── B.3 Navigation & Findability       │
│  ├── A.4 AI / GEO Discoverability       │ │  ├── B.4 CTA & User Journey             │
│  │   ├── Structural AI Readiness        │ │  ├── B.5 Performance & Stability        │
│  │   └── Observed AI Visibility Testing │ │  ├── B.6 Mobile UX & Responsiveness     │
│  ├── A.5 Machine Readability & Entity   │ │  ├── B.7 Trust, Credibility & Compliance│
│  └── A.6 Freshness & Corroboration      │ │  ├── B.8 Observable Accessibility       │
│                                         │ │  └── B.9 AI-Agent Interaction Readiness │
└─────────────────────────────────────────┘ └─────────────────────────────────────────┘
                     │                                           │
                     └─────────────────────┬─────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │              4. Evidence Validation Engine            │
               │   (Enforce Fact Grounding & Reject Unanchored Claims) │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │             5. Audit-Derived Scoring Engine           │
               │   (Normalized 0–100 Indexes & Severity Penalty Caps)  │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │            6. Actionable Remediation Engine           │
               │     (Map Finding ➔ Evidence ➔ Impact ➔ Specific Fix)  │
               └───────────────────────────┬───────────────────────────┘
                                           │
                                           ▼
               ┌───────────────────────────────────────────────────────┐
               │               7. Final Audit Deliverables             │
               │     (Structured JSON Artifact & Executive Report)     │
               └───────────────────────────────────────────────────────┘
```

---

## 🧩 Agent Skill Marketplace Summary

The package exposes a master orchestrator entrypoint and six specialized modular sub-skills:

| Skill | Path | Description |
| :--- | :--- | :--- |
| **`audit-orchestrator`** *(Entrypoint)* | [`skills/audit-orchestrator/SKILL.md`](skills/audit-orchestrator/SKILL.md) | Coordinates the end-to-end audit, derives brand context, executes empirical AI visibility queries, aggregates evidence, and computes normalized scores. |
| **`crawl-render-audit`** | [`skills/crawl-render-audit/SKILL.md`](skills/crawl-render-audit/SKILL.md) | Audits AI crawler `robots.txt` permissions, HTTP headers, pre-JS vs post-JS DOM delta (CSR vs SSR), sitemaps, and Core Web Vitals. |
| **`structured-data-audit`** | [`skills/structured-data-audit/SKILL.md`](skills/structured-data-audit/SKILL.md) | Validates Schema.org JSON-LD (`Organization`, `Product`, `FAQPage`, `Article`), Microdata, OpenGraph, and semantic HTML5 elements. |
| **`fact-quality-audit`** | [`skills/fact-quality-audit/SKILL.md`](skills/fact-quality-audit/SKILL.md) | Extracts atomic propositions, detects cross-page contradictions, evaluates claim precision, and scores AI hallucination vulnerability. |
| **`freshness-corroboration`** | [`skills/freshness-corroboration/SKILL.md`](skills/freshness-corroboration/SKILL.md) | Inspects temporal metadata (`dateModified`, `<lastmod>`), detects stale core pages, and cross-checks observable external corroboration. |
| **`entity-identity-audit`** | [`skills/entity-identity-audit/SKILL.md`](skills/entity-identity-audit/SKILL.md) | Automatically derives canonical brand identity and audits cross-page Name-Address-Phone (NAP) uniformity and `sameAs` entity links. |
| **`engagement-audit`** | [`skills/engagement-audit/SKILL.md`](skills/engagement-audit/SKILL.md) | Evaluates comprehensive on-site engagement across first-visit clarity, scannability, navigation, CTA journeys, mobile UX, trust, and AI-agent protocols. |

---

## 📊 Concept Audit Report Preview

```
Brand AI Readiness Audit
─────────────────────────────────────────────────────────────
Target Domain: example.com
Overall Brand AI Readiness Score: 78 / 100

Off-site Discoverability: 72 / 100
On-site Engagement:       84 / 100

DIMENSION A: OFF-SITE DISCOVERABILITY (72/100)
─────────────────────────────────────────────────────────────
• On-page SEO & Content Quality:      81 / 100
• Technical SEO & Crawlability:       76 / 100
• Off-page Authority & Reputation:    61 / 100  (Observable signals)
• AI / GEO Discoverability:           69 / 100  (Structural: 78, Observed: 60)
• Machine Readability & Entity:       82 / 100
• Freshness & Corroboration:          73 / 100

DIMENSION B: ON-SITE ENGAGEMENT (84/100)
─────────────────────────────────────────────────────────────
• First-Visit Clarity:                91 / 100
• Content Scannability:               86 / 100
• Navigation & Findability:           88 / 100
• CTA & User Journey:                 79 / 100
• Performance & Stability:            75 / 100
• Mobile UX & Responsiveness:         90 / 100
• Trust, Credibility & Compliance:    83 / 100
• Observable Accessibility:           81 / 100
• AI-Agent Interaction Readiness:     62 / 100

TOP CRITICAL FINDINGS
─────────────────────────────────────────────────────────────
1. [FIND-AI-001] [High] AI Discovery Omission: Categorical query "best project management tools for startups" cited 4 competitors with 0 mentions of example.com.
   Evidence: EVID-AI-VISIBILITY-003
   Fix: Deploy targeted /llms.txt summary and Schema FAQPage on /features.

2. [FIND-FACT-002] [Critical] Pricing Contradiction: /pricing states "$49/mo Starter plan", while /faq states "$39/mo Starter plan".
   Evidence: EVID-TEXT-BLOCKS-014, EVID-TEXT-BLOCKS-088
   Fix: Harmonize pricing tiers across all informational templates.

3. [FIND-CRAWL-003] [High] CSR Blocking: 62% of product feature specs are rendered via client-side JavaScript and absent in raw HTML.
   Evidence: EVID-DOM-RAW-002, EVID-DOM-RENDERED-002 (DOM Delta: 62%)
   Fix: Implement Server-Side Rendering (SSR) or dynamic pre-rendering for product pages.
```

---

## 📁 Repository Structure

```
brand-ai-readiness-audit/
├── README.md                          # Master project documentation
├── marketplace.json                   # Agent Skill Marketplace manifest
├── LICENSE                            # MIT License
├── .gitignore                         # Build and runtime ignore rules
│
├── docs/                              # Architecture and design specifications
│   ├── audit-matrix.md                # 2-Dimension signal, evidence, scoring & severity matrix
│   ├── architecture.md                # System pipeline, components, and evidence store design
│   ├── research.md                    # GEO, crawler behavior, and empirical research base
│   └── decisions.md                   # Architecture Decision Records (ADR-001 to ADR-006)
│
├── skills/                            # Specialized Agent Skills
│   ├── audit-orchestrator/            # Master entrypoint orchestrator skill
│   │   └── SKILL.md
│   ├── crawl-render-audit/            # Technical SEO & AI crawlability skill
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── references/
│   ├── structured-data-audit/         # Machine readability & Schema.org skill
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── references/
│   ├── fact-quality-audit/            # Proposition extraction & contradiction skill
│   │   ├── SKILL.md
│   │   └── references/
│   ├── freshness-corroboration/        # Temporal metadata & corroboration skill
│   │   ├── SKILL.md
│   │   └── references/
│   ├── entity-identity-audit/         # Canonical entity derivation & NAP skill
│   │   ├── SKILL.md
│   │   └── references/
│   └── engagement-audit/              # 9-pillar On-site engagement audit skill
│       ├── SKILL.md
│       └── references/
│
├── tests/                             # Test targets and validation schemas
│   ├── test-sites.json                # Test target site registry
│   ├── expected-findings.json         # Benchmark audit results schema
│   └── evaluation.md                  # Evaluation criteria and verification plan
│
├── src/                               # Core Python engine (Planned Phase 2)
│   ├── crawler/                       # Headless Playwright crawler & header extractors
│   ├── extraction/                    # DOM, JSON-LD, text proposition parsers
│   ├── analysis/                      # Deterministic checkers & LLM reasoning engine
│   └── reporting/                     # JSON & Markdown report generators
│
└── config/                            # Audit configuration
    └── audit-config.yaml              # Weights, timeouts, and bot definitions
```

---

## 🚀 Development Phases

- [x] **Phase 1: Conceptual Architecture & Skill Specifications** (Completed)
  - Unified two-dimensional audit framework (Off-site Discoverability & On-site Engagement).
  - Defined URL-only automated context discovery engine.
  - Established Evidence-First Architecture with strict Evidence ID traceability.
  - Specified Structural AI Readiness vs. Observed AI Visibility testing.
  - Designed Inferred Engagement framework (eliminating fabricated analytics).
  - Overhauled all 7 skill definitions and complete documentation suite.
- [ ] **Phase 2: Crawler Pipeline & Immutable Evidence Store**
- [ ] **Phase 3: Deterministic Parsers & Automated Context Synthesizer**
- [ ] **Phase 4: Specialized LLM Reasoning Evaluators & AI Visibility Engine**
- [ ] **Phase 5: Scoring Calibration, Benchmark Validation & CLI Interface**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
