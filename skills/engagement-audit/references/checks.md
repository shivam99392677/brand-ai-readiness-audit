# Engagement Audit - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| EG-01 | Landing Orientation (Who/What/Next) | High | Evaluates whether the landing screen immediately states who the brand is (H1), what it provides (subheading), and what the visitor should do next (actionable CTA) |
| EG-02 | Navigation Coverage of Offerings | Medium | Verifies that site navigation links route to key product and service offerings claimed in homepage headings |
| EG-03 | Interior Breadcrumb Hierarchy | Medium | Checks deep interior pages (depth >= 2) for breadcrumb hierarchy or parent navigation context |
| EG-04 | Actionable Call-to-Action (CTA) | Medium | Detects generic "Learn More" loops pointing back to the same page without real conversion actions |

## Guardrails
- FORBIDDEN as core defects: Missing /llms.txt, /openapi.json, or live chat widgets.
- JS-Shell Protection: Pages with <80 visible words not penalized under EG-01.
