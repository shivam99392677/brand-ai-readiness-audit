# Audit Orchestrator — Check List & Engine Design

This file contains the detailed check list and engine design for the
audit-orchestrator skill. The SKILL.md is the entrypoint; this file is for
reference.

## Orchestration Pipeline

1. **Validate URL** — scheme must be http/https, hostname non-empty.
2. **Crawl** — SiteCrawler discovers pages within max-pages / max-depth limits.
   Fetches robots.txt, sitemap.xml, and HTML for each page. Optionally renders
   JS-heavy pages via Playwright (bounded, with timeouts).
3. **Extract** — ExtractionManager produces a canonical evidence store
   (ExtractionResult) with sequential EV-00001 IDs.
4. **6 Specialist Audits** — each consumes the evidence store and returns a
   list of Findings:
   - crawl-render-audit (CR-001..CR-012)
   - structured-data-audit (SD-001..SD-006)
   - fact-quality-audit (FQ-01..FQ-04)
   - freshness-corroboration (FC-01..FC-03)
   - entity-identity-audit (EI-01..EI-03)
   - engagement-audit (EG-01..EG-04)
   Plus extended skills (run by default):
   - sitemap-audit (CR-013)
   - bot-block-audit (CR-014)
5. **Compose** — AdobeReportComposer filters non-defects, sorts by severity,
   and writes report.json.

## Content Rules (enforced across all skills)

- Every finding sentence must be backed by evidence a human can re-find on the
  live page in 30 seconds (a URL + a count or a quoted snippet).
- Reachability errors (robots.txt / sitemap.xml timeouts) are reported as
  **unscored/LOW**, never as site defects.
- "AI Bot Blocking" is only claimed when an explicit `Disallow: /` rule exists
  for a target bot.
- Missing schema / missing sameAs are **not** defects unless a product page or
  a declared Organization is involved.
- Footer copyright years are ignored for staleness checks.
- Do NOT fake ChatGPT citation counts.
- Do NOT emit "No JSON-LD on product pages" for non-product pages.

## Suggested Actions

- Targeted at the mechanism (if JS-empty → SSR or prerender, not "add keywords").
- Prioritized (high/medium/low).
- MAY include 1–3 proactive suggestions even with no defect
  (e.g. add FAQPage on docs, add sameAs if Organization exists).
- Never apply the fix to the live site.

## Forbidden as Core Defects

- Missing `/llms.txt`
- Missing `/openapi.json`
- Missing live chat widget

These may be mentioned as LOW proactive suggestions only.

## Report Schema

See SKILL.md Output section. Extra fields are allowed. Summary counts should
be consistent with findings[].severity distribution.
