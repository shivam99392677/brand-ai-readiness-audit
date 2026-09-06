---
name: Fact Quality Audit
description: Evaluates factual precision, claim verifiability, content clarity, cross-page contradictions, and AI hallucination vulnerability across brand text assets.
---

# Fact Quality Audit Skill

## Purpose
The **Fact Quality Audit** skill evaluates textual content across crawled brand pages to measure factual precision, semantic clarity, cross-page consistency, and vulnerability to AI hallucination during retrieval-augmented generation (RAG).

---

## When to Use
Invoked by `audit-orchestrator` during the semantic content analysis phase.

---

## Input Handling & Automated Context
**No user-provided context is required.** The skill receives internally derived brand context and extracted text blocks directly from the **Evidence Store**:
- `derived_brand_context`: Automatically synthesized brand name, offerings, and positioning.
- `extracted_text_blocks`: Cleaned DOM text nodes mapped to source URLs and CSS selectors.

---

## High-Level Responsibilities

1. **Atomic Proposition Extraction**:
   - Parses narrative text into atomic, testable factual propositions across:
     - Pricing tiers, fees, billing cadences, discounts.
     - Product specifications, system requirements, supported platforms.
     - Core features, capabilities, limits, quotas.
     - Commercial terms, SLA guarantees, trial periods, refund policies.
     - Statistical claims, benchmarks, performance metrics.

2. **Cross-Page Contradiction Detection**:
   - Compares propositions across different landing pages to detect factual conflicts.
   - *Example Finding*: Pricing Page states *"14-day free trial, no credit card required"*, but FAQ Page states *"30-day free trial with valid credit card"*.
   - *Example Finding*: Features page lists *"SOC2 Type II Certified"*, while Security page notes *"SOC2 Type I in progress"*.

3. **Ambiguity & Vagueness Evaluation**:
   - Identifies vague, under-specified copy that leaves AI models unable to provide definitive answers to user queries.
   - Evaluates whether technical specifications and feature descriptions are clear and complete.

4. **Hallucination Vulnerability Scoring**:
   - Analyzes text chunks for high semantic entropy or incomplete context that commonly causes LLM retrieval pipelines to hallucinate unsupported details.

5. **Marketing Hyperbole vs. Factual Claims**:
   - Accurately differentiates subjective promotional tone (*"Empowering teams worldwide"*) from objective factual claims (*"Guaranteed 99.99% uptime"*), preventing false-positive penalties on standard marketing copy.

---

## Inputs
- **`extracted_text_blocks`** *(array of objects, required)*: Text nodes with URL, selector, and text content from Evidence Store.
- **`derived_brand_context`** *(object, required)*: Internally derived brand profile.

---

## Outputs
- **`fact_quality_score`** *(number, 0–100)*: Normalized Fact Quality score.
- **`findings`** *(array of objects)*:
  - `finding_id`: Unique identifier (e.g., `FIND-FACT-001`).
  - `category`: `Factual & Content Quality`.
  - `severity`: `Critical` (direct pricing/spec contradiction) | `High` | `Medium` | `Low`.
  - `title`: Short summary.
  - `description`: Detailed explanation of the contradiction or ambiguity.
  - `impact`: How this causes AI models to generate conflicting or hallucinated answers.
  - `evidence_ids`: Referenced text block Evidence IDs (`EVID-TEXT-BLOCKS`).
  - `remediation`: Specific suggested text revision to harmonize facts.
- **`proposition_table`**: Structured array of extracted propositions categorized by type (pricing, feature, policy, stat).

---

## Evidence Expectations
- `EVID-TEXT-BLOCKS`: Raw text segments mapped to page URLs and DOM selector paths.
- `EVID-PROPOSITIONS`: Normalized table of atomic propositions.
- `EVID-CONTRADICTIONS`: Paired conflicting statement records with source locations.

---

## False-Positive Considerations
- **Subjective / Figurative Marketing Language**: Metaphors and aspirational taglines (*"The fastest way to scale your vision"*) should not be flagged as factual contradictions unless they make specific, falsifiable numerical claims.
- **Regional / Currency Variations**: A page displaying €99 in European locales and \$99 in US locales must not be flagged as a contradiction if regional path/locale indicators (`/eu/`, `/us/`, or `hreflang`) are present.
- **Tiered Product Editions**: Differences in features between "Starter", "Pro", and "Enterprise" tiers must be recognized as distinct product tiers, not contradictions.
