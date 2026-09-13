"""Entity Identity & NAP Consistency Audit Skill (EI-01 through EI-03).

Audits Organization/Brand naming uniformity between JSON-LD, <title>, and <h1>,
validates sameAs social/Knowledge Graph links, and checks cross-page Name-Address-Phone (NAP) consistency.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from src.evidence.models import WebsiteEvidence
from src.models import Evidence, Finding, FindingSeverity, FindingStatus
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, ExtractionResult


def normalize_phone_number(raw_phone: str) -> str:
    """Normalizes phone string into digits-only representation for exact comparison."""
    return re.sub(r"\D", "", raw_phone)


def normalize_name_str(name: str) -> str:
    """Normalizes brand name for fuzzy matching."""
    cleaned = re.sub(r"[^\w\s]", "", name.lower())
    # Remove common corporate suffixes for root comparison
    for suffix in ("inc", "llc", "ltd", "corp", "corporation", "co", "gmbh", "pvt", "limited"):
        cleaned = re.sub(rf"\b{suffix}\b", "", cleaned)
    return " ".join(cleaned.split())


class EntityIdentityAuditor:
    """Audits brand entity uniformity, NAP consistency, and sameAs link integrity."""

    def audit(
        self,
        evidence: ExtractionResult,
        website: Optional[WebsiteEvidence] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []

        try:
            # Group extracted entity evidence
            org_names_by_url: Dict[str, List[CanonicalEvidence]] = {}
            phones_by_url: Dict[str, List[CanonicalEvidence]] = {}
            addresses_by_url: Dict[str, List[CanonicalEvidence]] = {}
            same_as_by_url: Dict[str, List[CanonicalEvidence]] = {}
            titles_by_url: Dict[str, str] = {}
            h1s_by_url: Dict[str, List[str]] = {}

            for ev in evidence.evidence:
                u = ev.url or (website.start_url if website else "https://example.com")
                if ev.type == EvidenceType.ENTITY_NAME:
                    org_names_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.ENTITY_PHONE:
                    phones_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.ENTITY_ADDRESS:
                    addresses_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.SAME_AS_LINK:
                    same_as_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.PAGE_METADATA:
                    if ev.data.get("title"):
                        titles_by_url[u] = ev.data["title"]
                elif ev.type == EvidenceType.HEADING and ev.data.get("level") == 1:
                    h1s_by_url.setdefault(u, []).append(ev.data.get("text", ""))

            # Also ingest contacts directly from website.pages if available
            if website and hasattr(website, "pages") and website.pages:
                for page in website.pages:
                    p_url = page.url
                    if page.title:
                        titles_by_url.setdefault(p_url, page.title)
                    if hasattr(page, "contacts") and page.contacts:
                        for ph in page.contacts.phone_numbers:
                            phones_by_url.setdefault(p_url, []).append(CanonicalEvidence(
                                id="EV-CONT-PH",
                                type=EvidenceType.ENTITY_PHONE,
                                source="page_contacts",
                                url=p_url,
                                data={"phone": ph},
                                provenance={"source": "page.contacts", "source_url": p_url, "location": "DOM Contact Text"},
                            ))
                        for ad in page.contacts.addresses:
                            addresses_by_url.setdefault(p_url, []).append(CanonicalEvidence(
                                id="EV-CONT-AD",
                                type=EvidenceType.ENTITY_ADDRESS,
                                source="page_contacts",
                                url=p_url,
                                data={"address": ad},
                                provenance={"source": "page.contacts", "source_url": p_url, "location": "DOM Address Text"},
                            ))

            # -------------------------------------------------------------
            # EI-01: Organization / Brand Name Discrepancies
            # -------------------------------------------------------------
            name_discrepancy_evs: List[Evidence] = []
            all_schema_names: Set[str] = set()

            for u_url, ev_list in org_names_by_url.items():
                for ev in ev_list:
                    raw_n = ev.data.get("name", "").strip()
                    if raw_n:
                        all_schema_names.add(raw_n)

            # Collapse entity-name noise before judging conflicts:
            #  - drop FAQ-question strings ("Do you have setup fees?") which are
            #    FAQPage headings, not brand names;
            #  - drop office/branch names ("Stripe Berlin") when the root brand
            #    ("Stripe") is also declared — a branch is not a conflicting entity;
            #  - only Organization-like roots participate in the title comparison.
            def _is_question(n: str) -> bool:
                return "?" in n

            root_names = {n for n in all_schema_names if not _is_question(n)}
            single_roots = {n for n in root_names if len(n.split()) == 1}
            root_names = {
                n for n in root_names
                if len(n.split()) == 1
                or not any(normalize_name_str(n).startswith(normalize_name_str(s)) for s in single_roots)
            }

            # Check if multiple conflicting organization names are declared in Schema
            if len(root_names) > 1:
                norm_schema_roots = {normalize_name_str(n): n for n in root_names}
                if len(norm_schema_roots) > 1:
                    name_discrepancy_evs.append(Evidence(
                        source_url=website.start_url if website else "https://example.com",
                        evidence_type="schema_name_conflict",
                        observed={"declared_schema_names": sorted(list(root_names))},
                        location="JSON-LD Organization.name",
                    ))

            # Compare primary schema name against homepage Title & H1
            start_u = website.start_url if website else next(iter(titles_by_url.keys()), "https://example.com")
            home_title = titles_by_url.get(start_u, "")
            home_h1s = h1s_by_url.get(start_u, [])

            if root_names and home_title:
                norm_title = normalize_name_str(home_title)
                schema_name_matches = any(normalize_name_str(sn) in norm_title for sn in root_names)
                if not schema_name_matches and len(norm_title.split()) > 0:
                    # Potential mismatch
                    name_discrepancy_evs.append(Evidence(
                        source_url=start_u,
                        evidence_type="brand_title_mismatch",
                        observed={
                            "declared_schema_names": sorted(list(root_names)),
                            "page_title": home_title,
                        },
                        location="<head> > <title> vs JSON-LD",
                    ))

            if name_discrepancy_evs:
                findings.append(Finding(
                    skill="entity-identity-audit",
                    check_id="EI-01",
                    title="Brand Entity Name Discrepancy",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.HIGH,
                    description="Detected conflicting brand or organization names across Schema.org markup, page title, and headings.",
                    evidence=name_discrepancy_evs,
                    recommendation="Ensure the primary brand name in Organization JSON-LD strictly matches page titles and brand headers.",
                ))

            # -------------------------------------------------------------
            # EI-02: sameAs Link & Social Profile Verification
            # -------------------------------------------------------------
            all_same_as: Set[str] = set()
            for sa_list in same_as_by_url.values():
                for sa_ev in sa_list:
                    sa_url = sa_ev.data.get("same_as_url", "").strip()
                    if sa_url:
                        all_same_as.add(sa_url)

            invalid_same_as: List[str] = []
            broken_same_as: List[str] = []
            checked_sameas = 0

            import requests
            for sa_url in all_same_as:
                if not (sa_url.startswith("http://") or sa_url.startswith("https://")):
                    invalid_same_as.append(sa_url)
                elif checked_sameas < 2:
                    checked_sameas += 1
                    try:
                        resp = requests.get(sa_url, timeout=8.0, headers={"User-Agent": "Mozilla/5.0 (compatible; BrandAIReadinessAudit/1.0)"})
                        if resp.status_code == 404:
                            broken_same_as.append(sa_url)
                    except Exception:
                        pass  # Skip unreachable gracefully

            if invalid_same_as:
                findings.append(Finding(
                    skill="entity-identity-audit",
                    check_id="EI-02",
                    title="Invalid or Malformed sameAs URLs",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description=f"Discovered invalid or malformed sameAs entity URLs: {', '.join(invalid_same_as)}.",
                    evidence=[Evidence(
                        source_url=website.start_url if website else "https://example.com",
                        evidence_type="invalid_sameas_url",
                        observed={"invalid_urls": invalid_same_as},
                        location="Schema.org sameAs",
                    )],
                    recommendation="Ensure all sameAs entries are valid absolute HTTPS URLs.",
                ))
            elif broken_same_as:
                findings.append(Finding(
                    skill="entity-identity-audit",
                    check_id="EI-02",
                    title="Broken sameAs Entity Profile (404 Not Found)",
                    status=FindingStatus.FAIL,
                    severity=FindingSeverity.HIGH,
                    description=f"One or more declared sameAs entity URLs returned HTTP 404 Not Found: {', '.join(broken_same_as)}.",
                    evidence=[Evidence(
                        source_url=website.start_url if website else "https://example.com",
                        evidence_type="broken_sameas_url",
                        observed={"broken_urls": broken_same_as},
                        location="Schema.org sameAs",
                    )],
                    recommendation="Repair or remove broken sameAs profile URLs.",
                ))
            elif not all_same_as:
                # Missing sameAs is only a LOW suggestion when an Organization/Brand
                # entity is actually declared (so sameAs could be attached to it).
                # Sites with no Organization entity (e.g. placeholder domains) are
                # NOT identity failures and must be skipped entirely.
                has_org_entity = any(
                    (ev.data.get("name") or "").strip()
                    for ev_list in org_names_by_url.values() for ev in ev_list
                )
                if has_org_entity:
                    findings.append(Finding(
                        skill="entity-identity-audit",
                        check_id="EI-02",
                        title="Missing Canonical sameAs Social Profiles",
                        status=FindingStatus.WARNING,
                        severity=FindingSeverity.LOW,
                        description="Organization entity is declared but no sameAs entity reference links were discovered in structured markup.",
                        evidence=[Evidence(
                            source_url=website.start_url if website else "https://example.com",
                            evidence_type="missing_sameas",
                            observed={"same_as_count": 0},
                            location="Schema.org sameAs",
                        )],
                        recommendation="Add sameAs URLs to Organization schema linking to official social profiles and Knowledge Graph entities.",
                    ))
                # else: no Organization entity declared -> skip entirely

            # -------------------------------------------------------------
            # EI-03: Name, Address, Phone (NAP) Consistency Across Pages
            # -------------------------------------------------------------
            nap_conflict_evs: List[Evidence] = []

            # 3a. Phone Number Conflicts
            phone_by_page: Dict[str, Set[str]] = {}
            for u_url, p_evs in phones_by_url.items():
                for p in p_evs:
                    raw_ph = p.data.get("phone", "").strip()
                    digits = normalize_phone_number(raw_ph)
                    if len(digits) >= 7:
                        phone_by_page.setdefault(u_url, set()).add(digits)

            all_unique_phones = set()
            for p_set in phone_by_page.values():
                all_unique_phones.update(p_set)

            if len(phone_by_page) > 1 and len(all_unique_phones) > 1:
                # Check for phone conflicts between distinct pages
                urls_list = list(phone_by_page.keys())
                for i in range(len(urls_list)):
                    for j in range(i + 1, len(urls_list)):
                        u1, u2 = urls_list[i], urls_list[j]
                        s1, s2 = phone_by_page[u1], phone_by_page[u2]
                        if s1 != s2 and not s1.issubset(s2) and not s2.issubset(s1):
                            nap_conflict_evs.append(Evidence(
                                source_url=u1,
                                evidence_type="phone_nap_conflict",
                                observed={"url": u1, "phones": sorted(list(s1)), "conflicting_url": u2, "conflicting_phones": sorted(list(s2))},
                                location="Page Contact / Phone",
                            ))
                            nap_conflict_evs.append(Evidence(
                                source_url=u2,
                                evidence_type="phone_nap_conflict",
                                observed={"url": u2, "phones": sorted(list(s2)), "conflicting_url": u1, "conflicting_phones": sorted(list(s1))},
                                location="Page Contact / Phone",
                            ))
                            nap_conflict_evs.append(Evidence(
                                source_url=u1,
                                evidence_type="phone_number_conflict",
                                observed={"url": u1, "phones": sorted(list(s1)), "conflicting_url": u2, "conflicting_phones": sorted(list(s2))},
                                location="Contact Info / DOM Text",
                            ))

            # 3b. Address Conflicts
            addr_by_page: Dict[str, Set[str]] = {}
            for u_url, a_evs in addresses_by_url.items():
                for a in a_evs:
                    raw_ad = a.data.get("address", "").strip()
                    if len(raw_ad) > 5:
                        addr_by_page.setdefault(u_url, set()).add(raw_ad)

            all_unique_addrs = set()
            for a_set in addr_by_page.values():
                all_unique_addrs.update(a_set)

            if len(addr_by_page) > 1 and len(all_unique_addrs) > 1:
                u_list = list(addr_by_page.keys())
                for i in range(len(u_list)):
                    for j in range(i + 1, len(u_list)):
                        u1, u2 = u_list[i], u_list[j]
                        ad1, ad2 = addr_by_page[u1], addr_by_page[u2]
                        if ad1 != ad2 and not ad1.issubset(ad2) and not ad2.issubset(ad1):
                            nap_conflict_evs.append(Evidence(
                                source_url=u1,
                                evidence_type="address_conflict",
                                observed={"url": u1, "addresses": sorted(list(ad1)), "conflicting_url": u2, "conflicting_addresses": sorted(list(ad2))},
                                location="Contact Info / PostalAddress",
                            ))

            if nap_conflict_evs:
                findings.append(Finding(
                    skill="entity-identity-audit",
                    check_id="EI-03",
                    title="Cross-Page NAP (Name, Address, Phone) Inconsistency",
                    status=FindingStatus.FAIL,
                    severity=FindingSeverity.HIGH,
                    description="Identified conflicting phone numbers or physical addresses across different site pages.",
                    evidence=nap_conflict_evs,
                    recommendation="Harmonize phone numbers and physical addresses across footer, contact pages, and Organization schema.",
                ))

        except Exception as err:
            findings.append(Finding(
                skill="entity-identity-audit",
                check_id="EI-ERR",
                title="Entity Identity Audit Error",
                status=FindingStatus.ERROR,
                severity=FindingSeverity.HIGH,
                description=f"Entity identity audit encountered an error: {str(err)}",
                evidence=[Evidence(source_url="https://example.com", evidence_type="error", observed={"error": str(err)})],
                recommendation="Inspect entity markup and contact candidate data.",
            ))

        return findings


def run_entity_identity_audit(
    evidence: ExtractionResult,
    website: Optional[WebsiteEvidence] = None,
) -> List[Finding]:
    """Canonical entrypoint for entity identity audit skill."""
    auditor = EntityIdentityAuditor()
    return auditor.audit(evidence=evidence, website=website)
