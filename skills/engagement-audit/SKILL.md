---
name: engagement-audit
description: Evaluates on-site human visitor orientation, above-the-fold clarity (Who/What/Next), navigation coverage, breadcrumbs, and actionable CTAs.
---

# On-Site Visitor Engagement Audit Skill

## Purpose
Evaluates how clearly and effectively a website presents core orientation information to human visitors and AI agents navigating the user experience. Focuses on visitor clarity, navigation discoverability, page context hierarchy, and actionable next steps.

## Operational Constraints & Capabilities
- **Allowed Tools:** GET HTTP, parse HTML, no writes.
- **Code Entrypoint:** `src/analysis/engagement_audit.py`
- **Output:** `List[Finding]` consumed by composer.

## When to Use
Invoked by `audit-orchestrator` during the visitor engagement and orientation analysis phase.

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`EG-01`** | **Landing Orientation (Who/What/Next)** | High | Evaluates whether the landing screen immediately states who the brand is (H1), what it provides (subheading), and what the visitor should do next (actionable CTA). |
| **`EG-02`** | **Navigation Coverage of Offerings** | Medium | Verifies that site navigation links route to key product and service offerings claimed in homepage headings. |
| **`EG-03`** | **Interior Breadcrumb Hierarchy** | Medium | Checks deep interior pages (depth >= 2) for breadcrumb hierarchy or parent navigation context. |
| **`EG-04`** | **Actionable Call-to-Action (CTA)** | Medium | Detects generic "Learn More" loops pointing back to the same page without real conversion actions. |

## Guardrails
- Strictly evaluates human and agent visitor orientation.
- **FORBIDDEN as core defects:** Missing `/llms.txt`, `/openapi.json`, or live chat widgets are never flagged as defects.
- **JS-Shell Protection:** Pages with low visible word count (<80 words) or pre-render JS shells are not penalized under `EG-01` so `crawl-render-audit` (`CR-010`) owns rendering issues without double-counting.

## Code Entrypoint & Tests
- Implementation module: `src/analysis/engagement_audit.py`
- Unit tests: `tests/test_analysis_skills.py`
