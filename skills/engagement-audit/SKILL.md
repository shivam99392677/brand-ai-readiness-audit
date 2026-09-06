---
name: On-Site Engagement Audit
description: Evaluates comprehensive on-site visitor and agent engagement across first-visit clarity, scannability, navigation, CTA journeys, performance, mobile UX, trust, accessibility, and AI-agent readiness.
---

# On-Site Engagement Audit Skill

## Purpose
The **On-Site Engagement Audit** skill evaluates how effectively a website helps human visitors and autonomous AI agents understand what the brand offers, navigate information, consume content, trust the company, and complete desired actions.

---

## Conceptual Correction & Scope
**Important Design Principle**: On-site engagement is **NOT** defined merely by `/llms.txt`, OpenAPI endpoints, or chatbots. AI-agent interoperability is only one supporting sub-pillar within a comprehensive 9-pillar engagement evaluation framework.

Furthermore, under the **URL-only input constraint**, private behavioral analytics (e.g., bounce rate, average session duration, conversion funnel drop-off) cannot be observed. The system **strictly avoids fabricating analytics** and instead infers engagement from deterministically observable technical, visual, structural, and informational attributes.

---

## When to Use
Invoked by `audit-orchestrator` to evaluate Dimension B (On-site Engagement).

---

## The 9 On-Site Engagement Sub-Pillars

```
                               On-Site Engagement (0–100)
                                           │
 ┌──────────────────┬──────────────────────┼──────────────────────┬──────────────────┐
 ▼                  ▼                      ▼                      ▼                  ▼
B.1 First-Visit    B.2 Content            B.3 Navigation         B.4 CTA & User     B.5 Performance
    Clarity            Scannability           & Findability          Journey            & Stability
 (18% weight)       (12% weight)           (14% weight)           (15% weight)       (12% weight)

 ┌──────────────────┼──────────────────────┼──────────────────────┤
 ▼                  ▼                      ▼                      ▼
B.6 Mobile UX      B.7 Trust &            B.8 Observable         B.9 AI-Agent
    & Responsive       Credibility            Accessibility          Readiness
 (10% weight)       (8% weight)            (6% weight)            (5% weight)
```

---

### 1. First-Visit Clarity (18% Weight)
- **Evaluation Signals**:
  - Above-the-fold value proposition: prominent `<h1>` headline, descriptive subheadline, and clear problem/solution explanation.
  - Immediate comprehension of core product/service offerings.
  - Visible primary call-to-action (CTA) above the fold.
  - Visual relevance of hero imagery or product previews.
- **Evidence**: `EVID-HERO-VIEWPORT` (above-the-fold DOM snapshot and screenshot).

### 2. Content Engagement & Scannability (12% Weight)
- **Evaluation Signals**:
  - Paragraph density (absence of unbroken text blocks >300 words).
  - Use of bulleted lists (`<ul>`, `<ol>`), comparison tables, and callout containers.
  - Heading utility: descriptive `<h2>`/`<h3>` tags enabling rapid visual scanning.
  - Readability indices: Flesch Reading Ease and Flesch-Kincaid Grade Level matched to target audience.
- **Evidence**: `EVID-READABILITY-SCORES` (computed readability metrics, paragraph word counts).

### 3. Navigation & Findability (14% Weight)
- **Evaluation Signals**:
  - Header & footer navigation clarity, structure, and label descriptiveness.
  - Key page discoverability: Pricing, Docs/Help, Contact, and About accessible within <=2 clicks from root.
  - Structured breadcrumb navigation on deep content pages.
  - Internal search availability: functional search input with transparent query handling.
  - Absence of orphan or dead-end leaf pages.
- **Evidence**: `EVID-NAV-TREE` (crawl depth graph, header/footer link matrix).

### 4. CTA & User Journey (15% Weight)
- **Evaluation Signals**:
  - Primary CTA clarity: distinct, action-oriented button copy ("Start Free Trial", "Book Demo").
  - Visual prominence: high color contrast against background, prominent sizing.
  - Conversion friction: form simplicity, field count (<=5 fields on initial lead forms).
  - Competing CTA hierarchy: clear visual distinction between primary and secondary actions.
  - Journey integrity: 100% of CTA links resolve to valid, functional destination URLs (0 broken links).
- **Evidence**: `EVID-CTA-ELEMENTS` (button contrast logs, form input counts, link status traces).

### 5. Performance & Interactive Stability (12% Weight)
- **Evaluation Signals**:
  - Time to First Byte (TTFB < 800ms).
  - Largest Contentful Paint (LCP <= 2.5s).
  - Cumulative Layout Shift (CLS <= 0.1).
  - Interaction to Next Paint (INP) / Total Blocking Time (TBT < 300ms).
  - Asset optimization (WebP/AVIF images, minified JS/CSS).
- **Evidence**: `EVID-PERF-METRICS` (browser performance trace and asset waterfall).

### 6. Mobile UX & Responsiveness (10% Weight)
- **Evaluation Signals**:
  - Viewport configuration: `<meta name="viewport" content="width=device-width, initial-scale=1">`.
  - Responsive layout: absence of horizontal page overflow (`scrollWidth <= clientWidth`).
  - Touch target ergonomics: buttons and interactive links >=48x48px with adequate spacing.
  - Mobile navigation: functional hamburger menu and sticky mobile header.
  - Desktop-to-mobile content parity (core pricing, features, and specs intact on mobile).
- **Evidence**: `EVID-MOBILE-VIEWPORT` (mobile DOM render, touch target audit table).

### 7. Trust, Credibility & Compliance (8% Weight)
- **Evaluation Signals**:
  - Company transparency: dedicated About Us, physical address, business registration / legal entity name.
  - Direct contact channels: functional Contact page, support email, phone numbers.
  - Legal compliance: accessible Privacy Policy and Terms of Service links.
  - Commercial credibility: transparent pricing disclosures, refund policies, SLA guarantees.
  - Social proof: verified customer logos, case studies, client testimonials, security certifications (SOC2, ISO).
- **Evidence**: `EVID-TRUST-SIGNALS` (legal URL verification, contact regex matches, social proof elements).

### 8. Observable Accessibility (6% Weight)
- **Evaluation Signals**:
  - Document language attribute (`<html lang="...">`).
  - Form accessibility: explicit `<label>` tags associated with form inputs via `for`/`id`.
  - Accessible names: all `<button>` and `<a>` elements have text or `aria-label`.
  - Color contrast meeting WCAG AA (>= 4.5:1 for standard body text).
  - Keyboard focus visibility on interactive controls.
- **Evidence**: `EVID-A11Y-AUDIT` (automated WCAG AA observable compliance log).

### 9. AI-Agent Interaction Readiness (5% Weight)
- **Evaluation Signals**:
  - Machine-readable summary: presence and validity of `/llms.txt` and `/llms-full.txt`.
  - API discovery: discoverable OpenAPI specifications (`/openapi.json`, `/.well-known/openapi.yaml`).
  - Transparent search: predictable query parameter structure (e.g., `/search?q=...`).
  - Structured action selectors (`data-*` attributes for reliable agentic form interaction).
- **Evidence**: `EVID-AGENT-PROTOCOLS` (`/llms.txt` HTTP response, OpenAPI discovery logs).

---

## Inputs
- **`rendered_dom_snapshots`** *(array of DOM documents, required)*: From Evidence Store.
- **`viewport_screenshots`** *(array of image buffers, optional)*: Desktop & Mobile renders.
- **`performance_metrics`** *(object, required)*: Core Web Vitals and timing data.

---

## Outputs
- **`on_site_engagement_score`** *(number, 0–100)*: Composite Dimension B score.
- **`sub_scores`** *(object)*: Individual 0–100 scores across all 9 engagement sub-pillars.
- **`findings`** *(array of objects)*:
  - `finding_id`: Unique identifier (e.g., `FIND-ENGAGE-001`).
  - `category`: Specific sub-pillar name.
  - `severity`: `Critical` | `High` | `Medium` | `Low`.
  - `title`: Short descriptive title.
  - `description`: Detailed observable UX or technical defect.
  - `impact`: Impact on visitor retention, understanding, or conversion.
  - `evidence_ids`: Referenced Evidence IDs (`EVID-HERO-VIEWPORT`, etc.).
  - `remediation`: Specific, actionable remediation advice.

---

## False-Positive Considerations
- **Non-Profit / Editorial Sites**: Informational portals without commercial products should not be penalized for lacking "Buy Now" CTAs.
- **Single-Page Sites**: Micro-apps with all content on a single page should not be penalized for low crawl depth or short menu hierarchies.
- **Minimalist Luxury Brands**: Minimalist hero designs for globally iconic brands should be evaluated with nuance regarding value proposition clarity.
