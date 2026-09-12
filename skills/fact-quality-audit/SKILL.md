---
name: fact-quality-audit
description: Evaluates factual consistency across pages, numerical clarity and units, ungrounded marketing superlatives, and proposition precision.
---

# Fact Quality Audit Skill

## Purpose
Evaluates textual content across brand pages to measure claim precision, semantic clarity, cross-page factual consistency (pricing, hours, refunds), and vulnerability to AI hallucination during retrieval-augmented generation (RAG).

## When to Use
Invoked by `audit-orchestrator` during the factual quality analysis phase.

## Standard Check Matrix

| Check ID | Check Title | Severity | Description |
| :--- | :--- | :--- | :--- |
| **`FQ-02`** | **Contradictory Proposition Claims** | High | Identifies conflicting pricing, refund policy windows, operating hours, or founding years across pages. |
| **`FQ-03`** | **Unitless Numeric Metrics** | Medium | Identifies numerical metrics lacking explicit units, benchmarks, or baseline comparators. |
| **`FQ-04`** | **Ungrounded Superlatives** | Medium | Flags marketing superlatives (`#1`, `best`, `only`, `leading`) lacking adjacent supporting citations or benchmark reports. |

## Code Entrypoint
- Implementation module: [`src/analysis/fact_quality_audit.py`](../../src/analysis/fact_quality_audit.py)
- Unit tests: [`tests/test_analysis_skills.py`](../../tests/test_analysis_skills.py)
