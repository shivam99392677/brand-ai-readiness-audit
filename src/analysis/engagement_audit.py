"""On-Site Visitor Engagement & Orientation Audit Skill (EG-01 through EG-04).

Evaluates above-the-fold clarity (Who/What/Next), navigation coverage of offerings,
interior page breadcrumb hierarchy, and actionable Call-to-Action (CTA) design.
This skill strictly evaluates visitor orientation and does NOT flag missing /llms.txt or /openapi.json.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from src.evidence.models import WebsiteEvidence
from src.models import Evidence, Finding, FindingSeverity, FindingStatus
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, ExtractionResult

ACTION_CTA_KEYWORDS = {
    "get started", "sign up", "signup", "register", "contact us", "contact",
    "request demo", "book demo", "try free", "start free", "buy now", "subscribe",
    "download", "schedule demo", "request audit", "get in touch", "apply now",
}

GENERIC_LOOP_CTA_KEYWORDS = {
    "learn more", "read more", "click here", "find out more", "discover more", "explore",
}


class EngagementAuditor:
    """Audits human visitor orientation, heading clarity, navigation coverage, and actionable CTAs."""

    def audit(
        self,
        evidence: ExtractionResult,
        website: Optional[WebsiteEvidence] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []

        try:
            start_u = website.start_url if website else "https://example.com"

            # Index extracted evidence by URL
            headings_by_url: Dict[str, List[CanonicalEvidence]] = {}
            paragraphs_by_url: Dict[str, List[CanonicalEvidence]] = {}
            links_by_url: Dict[str, List[CanonicalEvidence]] = {}
            forms_by_url: Dict[str, List[CanonicalEvidence]] = {}
            coverage_ev: Optional[CanonicalEvidence] = None

            for ev in evidence.evidence:
                u = ev.url or start_u
                if ev.type == EvidenceType.HEADING:
                    headings_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.PARAGRAPH:
                    paragraphs_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.LINK_ITEM:
                    links_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.FORM_ITEM:
                    forms_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.CRAWL_COVERAGE:
                    coverage_ev = ev

            # Identify Homepage items using normalized URL matching
            start_norm = start_u.rstrip("/")
            home_u = start_u

            home_headings = [h for u, hs in headings_by_url.items() if u.rstrip("/") == start_norm or urlparse(u).path.strip("/") == "" for h in hs]
            home_paragraphs = [p for u, ps in paragraphs_by_url.items() if u.rstrip("/") == start_norm or urlparse(u).path.strip("/") == "" for p in ps]
            home_links = [l for u, ls in links_by_url.items() if u.rstrip("/") == start_norm or urlparse(u).path.strip("/") == "" for l in ls]
            home_forms = [f for u, fs in forms_by_url.items() if u.rstrip("/") == start_norm or urlparse(u).path.strip("/") == "" for f in fs]

            # Check homepage word count to avoid double-counting JS-heavy shells (<80 words)
            home_word_count = 0
            for ev in evidence.evidence:
                ev_u_norm = (ev.url or "").rstrip("/")
                if (ev_u_norm == start_norm or urlparse(ev.url or "").path.strip("/") == "") and ev.type in (EvidenceType.VISIBLE_TEXT_SUMMARY, EvidenceType.TEXT_EXTRACTABILITY_SIGNAL):
                    home_word_count = ev.data.get("word_count", 0)
                    if home_word_count:
                        break
            if not home_word_count and website and hasattr(website, "pages") and website.pages:
                hp = next((p for p in website.pages if getattr(p, "url", "").rstrip("/") == start_norm or getattr(p, "depth", 1) == 0), None)
                if hp:
                    home_word_count = getattr(hp, "word_count", 0)
            if not home_word_count:
                all_home_text = " ".join([h.data.get("text", "") for h in home_headings] + [p.data.get("text", "") for p in home_paragraphs])
                home_word_count = len(all_home_text.split())

            # -------------------------------------------------------------
            # EG-01: First Screenful Missing Who / What / Next
            # -------------------------------------------------------------
            # Only fires when there is enough visible text (>=80 words) to judge orientation
            if home_word_count >= 80:
                has_h1 = any(h.data.get("level") == 1 and bool(h.data.get("text", "").strip()) for h in home_headings)
                has_subhead_or_desc = bool(home_paragraphs) or any(h.data.get("level") in (2, 3) for h in home_headings)

                # Check for primary CTA
                has_form_cta = bool(home_forms)
                has_button_cta = False
                for l_ev in home_links:
                    anchor = l_ev.data.get("anchor_text", "").strip().lower()
                    if any(k in anchor for k in ACTION_CTA_KEYWORDS):
                        has_button_cta = True
                        break

                missing_elements: List[str] = []
                if not has_h1:
                    missing_elements.append("Primary H1 (Who / What)")
                if not has_subhead_or_desc:
                    missing_elements.append("Descriptive Subhead / Value Proposition")
                if not has_form_cta and not has_button_cta:
                    missing_elements.append("Primary Actionable Call-to-Action (CTA)")

                if missing_elements:
                    findings.append(Finding(
                        skill="engagement-audit",
                        check_id="EG-01",
                        title="Landing Screen Missing Core Orientation Elements (Who/What/Next)",
                        status=FindingStatus.WARNING if len(missing_elements) == 1 else FindingStatus.FAIL,
                        severity=FindingSeverity.HIGH,
                        description=f"Homepage landing area is missing essential visitor orientation elements: {', '.join(missing_elements)}.",
                        evidence=[Evidence(
                            source_url=home_u,
                            evidence_type="landing_orientation",
                            observed={
                                "has_h1": has_h1,
                                "has_subhead": has_subhead_or_desc,
                                "has_action_cta": has_form_cta or has_button_cta,
                                "missing": missing_elements,
                                "word_count": home_word_count,
                            },
                            location="Homepage Above-The-Fold",
                        )],
                        recommendation="Ensure the primary screenful immediately states who the brand is (H1), what it provides (subheading), and what the visitor should do next (actionable CTA).",
                    ))

            # -------------------------------------------------------------
            # EG-02: Navigation Labels Do Not Cover Core Offerings
            # -------------------------------------------------------------
            h2_texts = [h.data.get("text", "").lower() for h in home_headings if h.data.get("level") == 2]
            # Skip statistic/counter H2s (e.g. "1,000,000+ articles") — a count is
            # not an offering, and comparing it to nav labels fabricates a finding
            # on portals and wikis.
            h2_texts = [t for t in h2_texts if not re.search(r"\d", t)]
            nav_link_texts = set(l.data.get("anchor_text", "").strip().lower() for l in home_links if l.data.get("is_internal"))

            uncovered_offerings: List[str] = []
            for h2 in h2_texts[:4]:
                words = [w for w in h2.split() if len(w) > 4]
                if words and not any(w in " ".join(nav_link_texts) for w in words):
                    uncovered_offerings.append(h2)

            if len(uncovered_offerings) >= 2 and nav_link_texts:
                findings.append(Finding(
                    skill="engagement-audit",
                    check_id="EG-02",
                    title="Site Navigation Does Not Cover Core Offerings",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description=f"Primary navigation does not clearly route to core service/product offerings declared in homepage headings: {', '.join(uncovered_offerings[:3])}.",
                    evidence=[Evidence(
                        source_url=home_u,
                        evidence_type="navigation_coverage",
                        observed={
                            "uncovered_headings": uncovered_offerings[:3],
                            "sample_nav_links": sorted(list(nav_link_texts))[:10],
                        },
                        location="<nav> vs <h2> Offerings",
                    )],
                    recommendation="Align top-level navigation labels with key product and service offerings declared in landing headings.",
                ))

            # -------------------------------------------------------------
            # EG-03: Interior Pages Lack Breadcrumb Context
            # -------------------------------------------------------------
            interior_pages_without_breadcrumbs: List[str] = []
            crawled_interior_urls: Set[str] = set(links_by_url.keys()) | set(paragraphs_by_url.keys()) | set(headings_by_url.keys())
            if website and hasattr(website, "pages") and website.pages:
                for p in website.pages:
                    if getattr(p, "url", ""):
                        crawled_interior_urls.add(p.url)
            for u_url in crawled_interior_urls:
                links_list = links_by_url.get(u_url, [])
                parsed = urlparse(u_url)
                path_depth = len([p for p in parsed.path.strip("/").split("/") if p])
                if path_depth >= 2:
                    # Check if breadcrumb or parent navigation link is present
                    has_breadcrumb = False
                    for l_ev in links_list:
                        anchor = l_ev.data.get("anchor_text", "").lower()
                        rel = str(l_ev.data.get("rel") or "").lower()
                        if "breadcrumb" in rel or "crumb" in anchor or "breadcrumbs" in anchor:
                            has_breadcrumb = True
                            break
                    if not has_breadcrumb:
                        # Visible parent-path navigation counts as breadcrumb context:
                        # a link whose target is the page's parent path (e.g. /about/
                        # on /about/team) gives the visitor a hierarchy to climb.
                        parent_path = parsed.path.rstrip("/").rsplit("/", 1)[0]
                        for l_ev in links_list:
                            tgt = urlparse(l_ev.data.get("target_url", "") or "")
                            if tgt.path and parent_path and tgt.path.rstrip("/") == parent_path:
                                has_breadcrumb = True
                                break
                    if not has_breadcrumb:
                        interior_pages_without_breadcrumbs.append(u_url)

            if interior_pages_without_breadcrumbs:
                findings.append(Finding(
                    skill="engagement-audit",
                    check_id="EG-03",
                    title="Deep Interior Pages Lack Breadcrumb Navigation",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description=f"Identified {len(interior_pages_without_breadcrumbs)} interior page(s) at depth >= 2 lacking breadcrumb hierarchy or parent navigation context.",
                    evidence=[Evidence(
                        source_url=u,
                        evidence_type="missing_breadcrumb",
                        observed={"url": u, "path_depth": len([p for p in urlparse(u).path.strip("/").split("/") if p])},
                        location="Interior Page Navigation",
                    ) for u in interior_pages_without_breadcrumbs[:5]],
                    recommendation="Add BreadcrumbList schema markup and visible breadcrumb navigation on deep interior pages to improve human and AI navigational understanding.",
                ))

            # -------------------------------------------------------------
            # EG-04: Primary CTA is a 'Learn More' Loop
            # -------------------------------------------------------------
            loop_ctas: List[Evidence] = []
            for u_url, links_list in links_by_url.items():
                for l_ev in links_list:
                    anchor = l_ev.data.get("anchor_text", "").strip().lower()
                    target_u = l_ev.data.get("target_url", "")
                    if any(loop_k in anchor for loop_k in GENERIC_LOOP_CTA_KEYWORDS):
                        # Check if target is just the same page or same section
                        if target_u == u_url or target_u.endswith("#") or (target_u and urlparse(target_u).path == urlparse(u_url).path):
                            loop_ctas.append(Evidence(
                                source_url=u_url,
                                evidence_type="cta_loop",
                                observed={"anchor_text": anchor, "target_url": target_u},
                                location=f"<a href='{target_u}'>",
                            ))

            if loop_ctas:
                findings.append(Finding(
                    skill="engagement-audit",
                    check_id="EG-04",
                    title="Call-to-Action Formats into Non-Actionable Loop",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description="Primary call-to-action uses generic looping text ('Learn More') pointing back to the same page without enabling a conversion or next step.",
                    evidence=loop_ctas,
                    recommendation="Replace generic 'Learn More' links with explicit action targets such as contact forms, product demo signups, or documentation portals.",
                ))

        except Exception as err:
            findings.append(Finding(
                skill="engagement-audit",
                check_id="EG-ERR",
                title="Engagement Audit Error",
                status=FindingStatus.ERROR,
                severity=FindingSeverity.HIGH,
                description=f"Engagement audit encountered an error: {str(err)}",
                evidence=[Evidence(source_url="https://example.com", evidence_type="error", observed={"error": str(err)})],
                recommendation="Inspect site page structure and navigation links.",
            ))

        return findings


def run_engagement_audit(
    evidence: ExtractionResult,
    website: Optional[WebsiteEvidence] = None,
) -> List[Finding]:
    """Canonical entrypoint for on-site visitor engagement and orientation audit skill."""
    auditor = EngagementAuditor()
    return auditor.audit(evidence=evidence, website=website)
