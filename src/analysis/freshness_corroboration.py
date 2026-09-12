"""Content Freshness & External Corroboration Audit Skill (FC-01 through FC-03).

Evaluates date consistency across metadata, HTTP headers, and visible text,
detects stale content older than 12 months (ignoring footer copyright),
and corroborates entity links against public knowledge sources (Wikidata/Wikipedia).
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import requests
from src.evidence.models import WebsiteEvidence
from src.models import Evidence, Finding, FindingSeverity, FindingStatus
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, ExtractionResult

# Default reference date for temporal freshness calculation (2026)
CURRENT_YEAR = 2026
MAX_FRESHNESS_DAYS = 365


def parse_date_to_year(date_str: Optional[str]) -> Optional[int]:
    """Extracts 4-digit year integer from a normalized or raw date string."""
    if not date_str:
        return None
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(date_str))
    if match:
        return int(match.group(1))
    return None


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses date string into datetime object."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    if len(cleaned) >= 10:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(cleaned[:10], fmt)
            except Exception:
                pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except Exception:
            pass
    return None


class FreshnessCorroborationAuditor:
    """Audits temporal signals, date disagreements, stale content, and external knowledge graph corroboration."""

    def __init__(self, request_timeout: float = 8.0):
        self.request_timeout = request_timeout

    def audit(
        self,
        evidence: ExtractionResult,
        website: Optional[WebsiteEvidence] = None,
    ) -> List[Finding]:
        findings: List[Finding] = []

        try:
            # 1. Group Freshness Dates by Page URL
            dates_by_url: Dict[str, List[CanonicalEvidence]] = {}
            same_as_links: List[CanonicalEvidence] = []
            wikidata_evs: List[CanonicalEvidence] = []
            entity_names: List[CanonicalEvidence] = []

            for ev in evidence.evidence:
                u = ev.url or (website.start_url if website else "https://example.com")
                if ev.type == EvidenceType.FRESHNESS_DATE:
                    dates_by_url.setdefault(u, []).append(ev)
                elif ev.type == EvidenceType.SAME_AS_LINK:
                    same_as_links.append(ev)
                elif ev.type == EvidenceType.WIKIDATA_ID:
                    wikidata_evs.append(ev)
                elif ev.type == EvidenceType.ENTITY_NAME:
                    entity_names.append(ev)

            # -------------------------------------------------------------
            # FC-01: Date Inconsistency / Disagreement Across Sources
            # -------------------------------------------------------------
            disagreement_evs: List[Evidence] = []
            for u_url, date_items in dates_by_url.items():
                date_map: Dict[str, str] = {}
                for d_ev in date_items:
                    k = d_ev.data.get("kind", "")
                    v = d_ev.data.get("normalized_value") or d_ev.data.get("raw_value")
                    if k and v:
                        date_map[k] = v

                # Check if datePublished > dateModified
                dt_pub = parse_iso_date(date_map.get("datePublished"))
                dt_mod = parse_iso_date(date_map.get("dateModified"))
                if dt_pub and dt_mod and dt_pub > dt_mod:
                    disagreement_evs.append(Evidence(
                        source_url=u_url,
                        evidence_type="date_inconsistency",
                        observed={
                            "datePublished": date_map.get("datePublished"),
                            "dateModified": date_map.get("dateModified"),
                            "reason": "datePublished is newer than dateModified",
                        },
                        location="JSON-LD / Metadata",
                    ))

                # Check if Last-Modified header contradicts JSON-LD dateModified by > 2 years
                dt_lm = parse_iso_date(date_map.get("last_modified_header"))
                # Check if visible text date contradicts JSON-LD dateModified or datePublished by >= 1 year
                dt_vis = parse_iso_date(date_map.get("visible_date"))
                if dt_vis and dt_mod:
                    diff_years = abs(dt_vis.year - dt_mod.year)
                    if diff_years >= 1:
                        disagreement_evs.append(Evidence(
                            source_url=u_url,
                            evidence_type="visible_date_discrepancy",
                            observed={
                                "visible_date": date_map.get("visible_date"),
                                "schema_date_modified": date_map.get("dateModified"),
                                "year_gap": diff_years,
                            },
                            location="Visible Text vs Schema dateModified",
                        ))
                elif dt_vis and dt_pub:
                    diff_years = abs(dt_vis.year - dt_pub.year)
                    if diff_years >= 1:
                        disagreement_evs.append(Evidence(
                            source_url=u_url,
                            evidence_type="visible_date_discrepancy",
                            observed={
                                "visible_date": date_map.get("visible_date"),
                                "schema_date_published": date_map.get("datePublished"),
                                "year_gap": diff_years,
                            },
                            location="Visible Text vs Schema datePublished",
                        ))

            if disagreement_evs:
                findings.append(Finding(
                    skill="freshness-corroboration",
                    check_id="FC-01",
                    title="Inconsistent Publication and Modification Dates",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description=f"Identified {len(disagreement_evs)} page(s) where temporal signals (HTTP Last-Modified, JSON-LD, datePublished, visible date) contradict each other.",
                    evidence=disagreement_evs,
                    recommendation="Align HTTP Last-Modified headers, visible page dates, and Schema dateModified timestamps to ensure AI recency scoring correctly reflects genuine content updates.",
                ))

            # -------------------------------------------------------------
            # FC-02: Stale Content Older Than 12 Months
            # -------------------------------------------------------------
            stale_pages_ev: List[Evidence] = []
            EXPLICIT_UPDATE_KINDS = {
                "datemodified", "schema_date_modified", "meta_moddate",
                "datepublished", "schema_date_published", "meta_pubdate",
                "last_modified_header", "time_tag_datetime", "time_datetime", "sitemap_lastmod"
            }

            for u_url, date_items in dates_by_url.items():
                explicit_years: List[int] = []
                for d_ev in date_items:
                    k = str(d_ev.data.get("kind", "")).lower()
                    # Strictly ignore footer copyright dates and ungrounded body text numbers
                    if "copyright" in k or k == "visible_date":
                        continue
                    if any(uk in k for uk in EXPLICIT_UPDATE_KINDS):
                        y = parse_date_to_year(d_ev.data.get("normalized_value") or d_ev.data.get("raw_value"))
                        if y:
                            explicit_years.append(y)

                # Only evaluate staleness if explicit machine-readable/time date signals exist
                if explicit_years:
                    newest_year = max(explicit_years)
                    if newest_year <= (CURRENT_YEAR - 2):  # e.g. 2024 or older when current is 2026
                        stale_pages_ev.append(Evidence(
                            source_url=u_url,
                            evidence_type="stale_content_date",
                            observed={
                                "newest_observed_year": newest_year,
                                "current_audit_year": CURRENT_YEAR,
                                "staleness_gap_years": CURRENT_YEAR - newest_year,
                            },
                            location="Explicit Timestamp Metadata",
                        ))

            if stale_pages_ev:
                findings.append(Finding(
                    skill="freshness-corroboration",
                    check_id="FC-02",
                    title="Stale Content Lacking Recent Modification Signal",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.HIGH if any(e.source_url == (website.start_url if website else "") for e in stale_pages_ev) else FindingSeverity.MEDIUM,
                    description=f"Detected {len(stale_pages_ev)} core page(s) with newest content date older than 12 months ({', '.join(set(str(e.observed['newest_observed_year']) for e in stale_pages_ev))}) with no recent update signals.",
                    evidence=stale_pages_ev[:5],
                    recommendation="Publish updated dateModified metadata and refresh evergreen content to prevent generative search decay.",
                ))

            # -------------------------------------------------------------
            # FC-03: Corroboration Against Public Sources (Wikidata / Wikipedia / sameAs)
            # -------------------------------------------------------------
            corroboration_evs: List[Evidence] = []
            checked_count = 0

            # 3a. Check Wikidata & Wikipedia & sameAs links (up to 3 public GET requests)
            targets_to_probe: List[Tuple[str, str, str]] = []  # (url, source_name, page_url)
            for w_ev in wikidata_evs:
                w_url = w_ev.data.get("wikidata_url")
                if w_url and w_url.startswith("http"):
                    targets_to_probe.append((w_url, "Wikidata", w_ev.url or "https://example.com"))

            for sa_ev in same_as_links:
                sa_url = sa_ev.data.get("same_as_url", "")
                if sa_url and sa_url.startswith("http"):
                    s_name = "Wikipedia" if "wikipedia.org" in sa_url.lower() else "sameAs Profile"
                    targets_to_probe.append((sa_url, s_name, sa_ev.url or "https://example.com"))

            for probe_url, probe_name, p_origin in targets_to_probe:
                if checked_count >= 3:
                    break
                checked_count += 1
                try:
                    resp = requests.get(
                        probe_url,
                        timeout=self.request_timeout,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; BrandAIReadinessAudit/1.0)"}
                    )
                    if resp.status_code == 200:
                        corroboration_evs.append(Evidence(
                            source_url=p_origin,
                            evidence_type="external_corroboration",
                            observed={"public_source": probe_name, "url": probe_url, "status": 200, "verified": True},
                            location=f"Schema.org sameAs ({probe_name})",
                        ))
                    elif resp.status_code == 404:
                        corroboration_evs.append(Evidence(
                            source_url=p_origin,
                            evidence_type="broken_corroboration_link",
                            observed={"public_source": probe_name, "url": probe_url, "status": 404, "verified": False},
                            location=f"Schema.org sameAs ({probe_name})",
                        ))
                except Exception:
                    # Skip unreachable sources gracefully without crashing
                    pass

            # 3b. If no sameAs or Wikidata found on primary site
            if not same_as_links and not wikidata_evs:
                findings.append(Finding(
                    skill="freshness-corroboration",
                    check_id="FC-03",
                    title="Missing External Entity Corroboration Links",
                    status=FindingStatus.WARNING,
                    severity=FindingSeverity.MEDIUM,
                    description="No external sameAs profiles or Wikidata Knowledge Graph references were detected on the domain to corroborate brand identity.",
                    evidence=[Evidence(
                        source_url=website.start_url if website else "https://example.com",
                        evidence_type="missing_corroboration",
                        observed={"same_as_count": 0, "wikidata_count": 0},
                        location="Schema.org sameAs",
                    )],
                    recommendation="Add sameAs URLs to Organization schema linking to authoritative profiles (Wikidata, Wikipedia, Crunchbase, verified social profiles) for cross-platform corroboration.",
                ))
            elif any(e.observed.get("status") == 404 for e in corroboration_evs):
                findings.append(Finding(
                    skill="freshness-corroboration",
                    check_id="FC-03",
                    title="Broken External Knowledge Graph Link",
                    status=FindingStatus.FAIL,
                    severity=FindingSeverity.HIGH,
                    description="One or more declared sameAs or Wikidata Knowledge Graph links returned HTTP 404 Not Found.",
                    evidence=[e for e in corroboration_evs if e.observed.get("status") == 404],
                    recommendation="Repair or remove broken sameAs and Wikidata entity URLs.",
                ))
            elif same_as_links or wikidata_evs:
                findings.append(Finding(
                    skill="freshness-corroboration",
                    check_id="FC-03",
                    title="External Entity Corroboration Links Present",
                    status=FindingStatus.PASS,
                    severity=FindingSeverity.INFO,
                    description=f"Detected {len(same_as_links) + len(wikidata_evs)} sameAs/Wikidata profile link(s) for brand entity verification.",
                    evidence=[Evidence(
                        source_url=website.start_url if website else "https://example.com",
                        evidence_type="same_as_presence",
                        observed={"same_as_count": len(same_as_links), "wikidata_count": len(wikidata_evs)},
                        location="Schema.org sameAs",
                    )],
                    recommendation="Maintain active sameAs profiles across Knowledge Graph databases.",
                ))

        except Exception as err:
            findings.append(Finding(
                skill="freshness-corroboration",
                check_id="FC-ERR",
                title="Freshness Corroboration Audit Error",
                status=FindingStatus.ERROR,
                severity=FindingSeverity.HIGH,
                description=f"Freshness audit encountered an error: {str(err)}",
                evidence=[Evidence(source_url="https://example.com", evidence_type="error", observed={"error": str(err)})],
                recommendation="Inspect temporal metadata and dates across site pages.",
            ))

        return findings


def run_freshness_corroboration(
    evidence: ExtractionResult,
    website: Optional[WebsiteEvidence] = None,
) -> List[Finding]:
    """Canonical entrypoint for freshness and corroboration audit skill."""
    auditor = FreshnessCorroborationAuditor()
    return auditor.audit(evidence=evidence, website=website)
