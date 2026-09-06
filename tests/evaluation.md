# Audit Evaluation & Verification Plan

This document outlines the testing methodology, ground truth benchmarks, and evaluation metrics used to validate the accuracy, reproducibility, and evidence grounding of the **Brand AI Readiness Audit** package.

---

## 1. Core Evaluation Goals

1. **Deterministic Accuracy:** Ensure 100% precision on rule-based checks (`robots.txt` parsing, JSON-LD syntax validation, HTTP header inspection, sitemap status verification).
2. **LLM Evidence Grounding:** Verify that 100% of LLM reasoning findings map back to valid raw Evidence IDs in the Evidence Store (Zero Un-anchored Claims).
3. **URL-Only Context Derivation Accuracy:** Benchmark the Automated Context Discovery Engine against known ground-truth brand profiles (name, offerings, value proposition, test query relevance).
4. **Reproducibility:** Guarantee identical deterministic scoring outputs when evaluating static DOM/header snapshot sets.
5. **Missing Evidence Protocol Compliance:** Verify that lack of observable third-party authority data is marked as `Unknown / Unavailable` rather than penalizing sites with 0/100 scores.
6. **False-Positive Minimization:** Benchmark hallucination flags, schema warnings, and engagement friction against human expert baseline audits.

---

## 2. Benchmark Target Dataset (`tests/test-sites.json`)

The test suite evaluates a curated list of diverse website architectures across both primary dimensions:
- **Client-Side Rendered (CSR):** Dynamic Single-Page Applications (React, Vue) to evaluate DOM delta and JS rendering resilience.
- **Server-Side Rendered (SSR):** Static blogs and CMS websites to test rapid text extraction and metadata precision.
- **E-Commerce Portals:** High-density catalog sites to validate `Product` / `Offer` schema compliance and CTA checkout journey integrity.
- **Enterprise B2B SaaS:** Technical platforms to test `/llms.txt`, OpenAPI discoverability, security disclosures, and navigation hierarchy.

---

## 3. Verification Metrics

- **Evidence Traceability Index (ETI)**:
  $$\text{ETI} = \frac{\text{Findings with Valid Evidence IDs}}{\text{Total Flagged Findings}} \quad (\text{Target: } 100\%)$$
- **Score Calibration Error (MAE)**: Mean Absolute Error between automated scores and human expert panel benchmark scores across both dimensions (Off-site Discoverability & On-site Engagement).
- **Precision on Factual Contradictions**: Precision rate in flagging genuine factual discrepancies vs marketing hyperbole.
- **Schema Validation Match Rate**: Agreement percentage between internal Schema checkers and official Schema.org validation standards.

---

## 4. Execution Workflow

```bash
# Run ground-truth benchmark suite (Phase 5 implementation)
pytest tests/
```
