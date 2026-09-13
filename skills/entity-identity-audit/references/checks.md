# Entity Identity Audit - Check Matrix

| Check ID | Title | Severity | What it evaluates |
| --- | --- | --- | --- |
| EI-01 | Brand Entity Name Discrepancy | High | Detects conflicts between Organization JSON-LD name, page title, and primary headings |
| EI-02 | sameAs Link & Social Verification | High / Medium | Validates sameAs entity profile URLs, detecting invalid URLs, 404 responses, or missing links |
| EI-03 | Cross-Page NAP Consistency | High | Flags conflicting phone numbers or physical addresses between contact pages, footers, and schema |

## Guardrails
- Missing sameAs is only a LOW suggestion when an Organization entity is declared.
- sameAs URLs validated with GET requests (timeout 8s, polite User-Agent).
