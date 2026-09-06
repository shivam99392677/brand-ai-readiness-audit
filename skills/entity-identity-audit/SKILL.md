---
name: Entity Identity & Consistency
description: Automatically derives canonical brand identity and audits cross-page Name-Address-Phone (NAP) uniformity, Organization schema, sameAs links, and Knowledge Graph alignment.
---

# Entity Identity & Consistency Skill

## Purpose
The **Entity Identity & Consistency** skill constructs a canonical understanding of the brand entity directly from website assets and audits all identity signals across pages. It ensures that search engines, AI knowledge graphs (Wikidata, Google Knowledge Graph), and LLM answer engines can build a unified, unambiguous entity model without entity fragmentation or brand confusion.

---

## When to Use
Invoked by `audit-orchestrator` during the semantic entity evaluation phase.

---

## Automated Canonical Profile Derivation
**No user-provided brand profile is required.** This skill automatically synthesizes the canonical brand identity by aggregating and cross-referencing:
1. `Organization` / `LocalBusiness` JSON-LD schema blocks (`name`, `legalName`, `logo`, `sameAs`, `contactPoint`).
2. Homepage `<title>`, OpenGraph `og:site_name`, and header brand logo alt text.
3. `/about`, `/contact`, and footer NAP (Name, Address, Phone) text disclosures.
4. Social profile links in navigation and footer regions.

---

## High-Level Responsibilities

1. **Canonical Profile Construction**:
   - Compiles a unified entity manifest: Brand Name, Legal Entity Name, Domain, Official Logo URL, Physical Address, Phone Numbers, Primary Contact Emails, and Social Profile URIs.

2. **Cross-Page NAP (Name, Address, Phone) Uniformity Audit**:
   - Scans all crawled pages to verify consistent presentation of:
     - Company Name & Trademark spelling.
     - Physical street addresses and headquarters location.
     - Customer support and sales phone numbers.
     - Official corporate email addresses.
   - Detects legacy addresses or conflicting phone numbers across regional or legacy sub-pages.

3. **`Organization` Schema & `sameAs` Authority Link Verification**:
   - Validates `sameAs` links pointing to authoritative knowledge profiles:
     - Wikidata (`https://www.wikidata.org/wiki/Q...`)
     - Wikipedia (`https://en.wikipedia.org/wiki/...`)
     - LinkedIn, Twitter/X, Crunchbase, GitHub, YouTube
   - Verifies that `sameAs` URLs resolve to valid, active profiles that match the brand identity.

4. **Logo & Asset Consistency**:
   - Verifies that official logo asset URLs declared in Schema match the primary visual brand assets rendered on the homepage.
   - Checks image dimensions, format, and transparency per Schema.org requirements.

5. **Entity Conflict & Disambiguation Analysis**:
   - Flags discrepancies between homepage branding and legal disclosures.
   - Detects if an outdated company name still lingers across older product or documentation pages.

---

## Inputs
- **`rendered_dom_snapshots`** *(array of DOM documents, required)*: From Evidence Store.
- **`extracted_schema_blocks`** *(array of JSON-LD objects, required)*: From Evidence Store.

---

## Outputs
- **`entity_consistency_score`** *(number, 0–100)*: Normalized Entity Consistency score.
- **`canonical_entity_profile`**: Derived JSON entity manifest (brand name, legal name, logo, NAP, sameAs).
- **`findings`** *(array of objects)*:
  - `finding_id`: Unique identifier (e.g., `FIND-ENTITY-001`).
  - `category`: `Machine Readability & Entity`.
  - `severity`: `Critical` (conflicting legal entity or broken sameAs) | `High` | `Medium` | `Low`.
  - `title`: Short summary.
  - `description`: Detailed explanation of entity conflict.
  - `impact`: Risk of AI models conflating the brand with unrelated entities.
  - `evidence_ids`: Referenced Evidence IDs (`EVID-NAP-BLOCKS`, `EVID-SAMEAS-LINKS`).
  - `remediation`: Step-by-step fix to align schema and on-page entity data.

---

## Evidence Expectations
- `EVID-NAP-BLOCKS`: Extracted text snippets containing brand name, address, and phone numbers.
- `EVID-SAMEAS-LINKS`: Extracted array of outbound profile links and HTTP status codes.
- `EVID-LOGO-ASSETS`: Extracted logo image URLs, dimensions, and DOM attributes.
- `EVID-CANONICAL-ENTITY`: The internally synthesized brand profile JSON.

---

## False-Positive Considerations
- **Parent vs. Subsidiary Entities**: If a site represents a subsidiary or product brand owned by a parent holding company, differences in legal name (e.g., "Slack Technologies, LLC" vs "Salesforce, Inc.") must not be penalized if parent relationships are declared.
- **Active Rebrand Transitions**: Recent brand name updates with legacy copyright notices in archive sections should be treated with Medium/Informational severity rather than Critical errors.
- **Regional Branches**: Distinct addresses across international offices (e.g., US vs UK headquarters) should be recognized as multiple valid locations under `Organization.department` or `Location`.
