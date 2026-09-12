---
name: entity-identity-audit
description: Audits brand entity naming consistency between title/H1 and schema, sameAs links, and cross-page NAP (Name, Address, Phone) uniformity.
---

# Entity Identity & Consistency Skill

## Purpose
Audits brand identity signals to ensure AI Knowledge Graphs and search engines can construct a unified, canonical entity model for the brand without entity fragmentation.

## When to Use
Invoked by `audit-orchestrator` during entity validation.

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`EI-01`** | **Brand Entity Name Discrepancy** | High | Detects conflicts between Organization JSON-LD name, page title, and primary headings. |
| **`EI-02`** | **sameAs Link & Social Verification** | High / Medium | Validates `sameAs` entity profile URLs, detecting invalid URLs, 404 responses, or missing links. |
| **`EI-03`** | **Cross-Page NAP Consistency** | High | Flags conflicting phone numbers or physical addresses between contact pages, footers, and schema. |

## Code Entrypoint
- Implementation module: [`src/analysis/entity_identity_audit.py`](../../src/analysis/entity_identity_audit.py)
- Unit tests: [`tests/test_analysis_skills.py`](../../tests/test_analysis_skills.py)
