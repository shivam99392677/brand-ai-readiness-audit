# Structured Data Audit - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| SD-001 | JSON-LD Detection | Info / Low | Detects presence of <script type="application/ld+json"> blocks |
| SD-002 | JSON-LD Parse Validity | High | Verifies that all detected JSON-LD blocks parse as valid JSON syntax |
| SD-003 | Schema Type Detection | Info | Extracts and lists declared @type schema values across the site |
| SD-004 | Entity Information Completeness | High / Medium / Info | Checks completeness of core properties for Product, Offer, Organization on applicable pages |
| SD-005 | Structured Data vs Visible Content Consistency | High | Verifies consistency between structured entity names and visible <title> / <h1> text |
| SD-006 | Duplicate or Conflicting Structured Data | Medium | Identifies multiple schema objects of the same type with conflicting canonical property values |

## Guardrails
- Only flags syntax errors or incomplete Product/Offer schemas on product pages.
- Missing schema on general pages is informational, not a defect.
