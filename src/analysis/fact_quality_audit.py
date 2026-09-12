"""Fact & Content Quality Audit Skill (FQ-01 through FQ-04).

Evaluates claim consistency, numerical clarity, ungrounded superlatives,
and cross-page contradictions across extracted text and structured evidence.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from src.evidence.models import WebsiteEvidence
from src.models import Evidence, Finding, FindingSeverity, FindingStatus
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, ExtractionResult

# Regex patterns for fact types
PRICE_REGEX = r"(?:[\$€£₹]\s*\d+(?:,\d{3})*(?:\.\d{1,2})?|\b\d+(?:,\d{3})*(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|INR|dollars|rupees)\b)"
HOURS_REGEX = r"\b(?:\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\s*[-–to]\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)|24/7|24\s*hours)\b"
REFUND_REGEX = r"\b(\d{1,3})\s*[-–\s]*(?:day|days)\s*(?:money[- ]back|refund|guarantee|return)\b"
FOUNDED_REGEX = r"\b(?:founded|established|since|operating since)\s*(?:in\s*)?([12]\d{3})\b"

SUPERLATIVE_PATTERNS = [
    r"\b#\s*1\b",
    r"\bnumber\s*(?:one|1)\b",
    r"\bworld'?s\s+(?:best|first|leading|fastest|most\s+\w+)\b",
    r"\b(?:the\s+)?best[- ]in[- ]class\b",
    r"\bthe\s+only\s+(?:\w+\s+){0,2}(?:platform|solution|product|provider|engine|service)\b",
    r"\bindustry[- ]leading\b",
    r"\bmarket[- ]leader\b",
    r"\bunmatched\s+(?:quality|performance|accuracy|reliability)\b",
]

CITATION_PATTERNS = [
    r"\baccording\s+to\b",
    r"\breport\b",
    r"\bgartner\b",
    r"\bforrester\b",
    r"\bidc\b",
    r"\bstudy\b",
    r"\bsurvey\b",
    r"\baward\b",
    r"\bcertified\s+by\b",
    r"\bverified\s+by\b",
    r"\bsource:\b",
    r"\[\d+\]",
    r"\biso\s*\d+\b",
]

# Patterns for numbers without units
UNITLESS_METRIC_REGEX = r"\b(?:increase[ds]?|decreased?|boost(?:ed)?|improve[ds]?|grow(?:th)?|faster|slower|reduced?)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s+(?!%|\bpercent\b|x\b|\bhours\b|\bsec\b|\bms\b|\bminutes\b|\bdays\b|\bpoints\b|\bclicks\b|\busers\b|\bclients\b|\bcustomers\b)([a-zA-Z]+)"


def run_fact_quality_audit(
    evidence: ExtractionResult,
    website: Optional[WebsiteEvidence] = None,
) -> List[Finding]:
    """Audits factual clarity, consistency, numerical qualifiers, and ungrounded superlatives."""
    findings: List[Finding] = []

    try:
        # Index evidence by URL and type
        text_by_url: Dict[str, List[Tuple[str, str, Optional[str]]]] = {}  # url -> [(text, ev_id, location)]
        price_claims: Dict[str, Set[Tuple[str, str]]] = {}  # url -> set of (raw_price, ev_id)
        refund_claims: Dict[str, Set[Tuple[int, str]]] = {}  # url -> set of (refund_days, ev_id)
        founded_claims: Dict[str, Set[Tuple[int, str]]] = {}  # url -> set of (founded_year, ev_id)
        hours_claims: Dict[str, Set[Tuple[str, str]]] = {}  # url -> set of (hours_str, ev_id)

        for ev in evidence.evidence:
            ev_url = ev.url or (website.start_url if website else "https://example.com")
            ev_id = ev.id or "EV-00000"
            loc = ev.provenance.location or ev.source

            # Collect text chunks from paragraphs, headings, blockquotes
            if ev.type in (EvidenceType.PARAGRAPH, EvidenceType.HEADING, EvidenceType.BLOCKQUOTE_BLOCK):
                text = ev.data.get("text", "").strip()
                if text:
                    text_by_url.setdefault(ev_url, []).append((text, ev_id, loc))

                    # Extract price mentions
                    prices = re.findall(PRICE_REGEX, text, re.IGNORECASE)
                    for pr in prices:
                        price_claims.setdefault(ev_url, set()).add((pr.strip(), ev_id))

                    # Extract refund days
                    refunds = re.findall(REFUND_REGEX, text, re.IGNORECASE)
                    for r in refunds:
                        try:
                            refund_claims.setdefault(ev_url, set()).add((int(r), ev_id))
                        except ValueError:
                            pass

                    # Extract founded year
                    founded = re.findall(FOUNDED_REGEX, text, re.IGNORECASE)
                    for f in founded:
                        try:
                            founded_claims.setdefault(ev_url, set()).add((int(f), ev_id))
                        except ValueError:
                            pass

                    # Extract hours mentions
                    hours_matches = re.findall(HOURS_REGEX, text, re.IGNORECASE)
                    for hm in hours_matches:
                        clean_hm = " ".join(hm.strip().split())
                        hours_claims.setdefault(ev_url, set()).add((clean_hm, ev_id))

        # -------------------------------------------------------------
        # FQ-02: Cross-Page Contradictions
        # -------------------------------------------------------------
        contradiction_evs: List[Evidence] = []
        contradiction_details: List[str] = []

        # 1. Price Contradictions
        if len(price_claims) > 1:
            urls_with_prices = list(price_claims.keys())
            for i in range(len(urls_with_prices)):
                for j in range(i + 1, len(urls_with_prices)):
                    u1, u2 = urls_with_prices[i], urls_with_prices[j]
                    p1_set = {p[0] for p in price_claims[u1]}
                    p2_set = {p[0] for p in price_claims[u2]}
                    if p1_set != p2_set and not p1_set.issubset(p2_set) and not p2_set.issubset(p1_set):
                        ev_ids1 = [p[1] for p in price_claims[u1]]
                        ev_ids2 = [p[1] for p in price_claims[u2]]
                        contradiction_details.append(
                            f"Pricing differs between {u1} ({', '.join(sorted(p1_set))}, [{', '.join(ev_ids1)}]) and {u2} ({', '.join(sorted(p2_set))}, [{', '.join(ev_ids2)}])."
                        )
                        contradiction_evs.append(Evidence(
                            source_url=u1,
                            evidence_type="price_claim",
                            observed={"url": u1, "prices": sorted(list(p1_set)), "evidence_ids": ev_ids1, "conflicting_url": u2, "conflicting_prices": sorted(list(p2_set))},
                            location="Page Text / Pricing",
                        ))
                        contradiction_evs.append(Evidence(
                            source_url=u2,
                            evidence_type="price_claim",
                            observed={"url": u2, "prices": sorted(list(p2_set)), "evidence_ids": ev_ids2, "conflicting_url": u1, "conflicting_prices": sorted(list(p1_set))},
                            location="Page Text / Pricing",
                        ))

        # 2. Refund Window Contradictions
        if len(refund_claims) > 1:
            refund_urls = list(refund_claims.keys())
            for i in range(len(refund_urls)):
                for j in range(i + 1, len(refund_urls)):
                    u1, u2 = refund_urls[i], refund_urls[j]
                    r1_set = {r[0] for r in refund_claims[u1]}
                    r2_set = {r[0] for r in refund_claims[u2]}
                    if r1_set != r2_set:
                        ev_ids1 = [r[1] for r in refund_claims[u1]]
                        ev_ids2 = [r[1] for r in refund_claims[u2]]
                        contradiction_details.append(
                            f"Refund policy window differs between {u1} ({r1_set} days, [{', '.join(ev_ids1)}]) and {u2} ({r2_set} days, [{', '.join(ev_ids2)}])."
                        )
                        contradiction_evs.append(Evidence(
                            source_url=u1,
                            evidence_type="refund_policy_claim",
                            observed={"url": u1, "refund_days": sorted(list(r1_set)), "evidence_ids": ev_ids1, "conflicting_url": u2, "conflicting_days": sorted(list(r2_set))},
                            location="Page Text / Policy",
                        ))
                        contradiction_evs.append(Evidence(
                            source_url=u2,
                            evidence_type="refund_policy_claim",
                            observed={"url": u2, "refund_days": sorted(list(r2_set)), "evidence_ids": ev_ids2, "conflicting_url": u1, "conflicting_days": sorted(list(r1_set))},
                            location="Page Text / Policy",
                        ))

        # 3. Founding Year Contradictions
        if len(founded_claims) > 1:
            f_urls = list(founded_claims.keys())
            for i in range(len(f_urls)):
                for j in range(i + 1, len(f_urls)):
                    u1, u2 = f_urls[i], f_urls[j]
                    f1_set = {f[0] for f in founded_claims[u1]}
                    f2_set = {f[0] for f in founded_claims[u2]}
                    if f1_set != f2_set:
                        ev_ids1 = [f[1] for f in founded_claims[u1]]
                        ev_ids2 = [f[1] for f in founded_claims[u2]]
                        contradiction_details.append(
                            f"Company founding year differs between {u1} ({f1_set}, [{', '.join(ev_ids1)}]) and {u2} ({f2_set}, [{', '.join(ev_ids2)}])."
                        )
                        contradiction_evs.append(Evidence(
                            source_url=u1,
                            evidence_type="founding_year_claim",
                            observed={"url": u1, "founded": sorted(list(f1_set)), "evidence_ids": ev_ids1, "conflicting_url": u2, "conflicting_founded": sorted(list(f2_set))},
                            location="Page Text / About",
                        ))
                        contradiction_evs.append(Evidence(
                            source_url=u2,
                            evidence_type="founding_year_claim",
                            observed={"url": u2, "founded": sorted(list(f2_set)), "evidence_ids": ev_ids2, "conflicting_url": u1, "conflicting_founded": sorted(list(f1_set))},
                            location="Page Text / About",
                        ))

        # 4. Operating Hours Contradictions
        if len(hours_claims) > 1:
            h_urls = list(hours_claims.keys())
            for i in range(len(h_urls)):
                for j in range(i + 1, len(h_urls)):
                    u1, u2 = h_urls[i], h_urls[j]
                    h1_set = {h[0] for h in hours_claims[u1]}
                    h2_set = {h[0] for h in hours_claims[u2]}
                    if h1_set != h2_set and not h1_set.issubset(h2_set) and not h2_set.issubset(h1_set):
                        ev_ids1 = [h[1] for h in hours_claims[u1]]
                        ev_ids2 = [h[1] for h in hours_claims[u2]]
                        contradiction_details.append(
                            f"Operating hours differ between {u1} ({h1_set}, [{', '.join(ev_ids1)}]) and {u2} ({h2_set}, [{', '.join(ev_ids2)}])."
                        )
                        contradiction_evs.append(Evidence(
                            source_url=u1,
                            evidence_type="hours_claim",
                            observed={"url": u1, "hours": sorted(list(h1_set)), "evidence_ids": ev_ids1, "conflicting_url": u2, "conflicting_hours": sorted(list(h2_set))},
                            location="Page Text / Contact & Hours",
                        ))
                        contradiction_evs.append(Evidence(
                            source_url=u2,
                            evidence_type="hours_claim",
                            observed={"url": u2, "hours": sorted(list(h2_set)), "evidence_ids": ev_ids2, "conflicting_url": u1, "conflicting_hours": sorted(list(h1_set))},
                            location="Page Text / Contact & Hours",
                        ))

        if contradiction_evs:
            findings.append(Finding(
                skill="fact-quality-audit",
                check_id="FQ-02",
                title="Contradictory Proposition Claims Across Pages",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                description="Found conflicting factual claims across different pages of the website: " + " ".join(contradiction_details),
                evidence=contradiction_evs,
                recommendation="Synchronize pricing, refund policies, operating hours, and organizational statistics across all site pages to prevent AI search models from citing contradictory information.",
            ))

        # -------------------------------------------------------------
        # FQ-03: Numbers Without Units / Comparators
        # -------------------------------------------------------------
        unitless_evs: List[Evidence] = []
        unitless_patterns = [
            UNITLESS_METRIC_REGEX,
            r"\b(?:over|more than|almost|nearly|up to|served|trusted by)\s+(\d{1,3}(?:,\d{3})+|\d{4,})\s+(?:across|throughout|in|every|yearly|worldwide|globally)\b",
            r"\b(\d{1,3}(?:,\d{3})+|\d{4,})\s+(?:across|throughout|every year|annually)\b",
        ]

        for u_url, chunks in text_by_url.items():
            for text, ev_id, loc in chunks:
                for upat in unitless_patterns:
                    matches = re.finditer(upat, text, re.IGNORECASE)
                    for m in matches:
                        matched_snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 20)]
                        unitless_evs.append(Evidence(
                            source_url=u_url,
                            evidence_type="unitless_metric",
                            observed={
                                "evidence_id": ev_id,
                                "number": m.group(1),
                                "context": matched_snippet,
                            },
                            location=loc,
                        ))

        if unitless_evs:
            findings.append(Finding(
                skill="fact-quality-audit",
                check_id="FQ-03",
                title="Unspecified Numeric Metrics Lacking Units or Baseline",
                status=FindingStatus.WARNING,
                severity=FindingSeverity.MEDIUM,
                description=f"Identified {len(unitless_evs)} numerical proposition(s) (e.g. '{unitless_evs[0].observed.get('number', '')}') lacking explicit units, percentages, or baseline comparators.",
                evidence=unitless_evs[:5],
                recommendation="Explicitly attach units (%, ms, $, x) and baseline benchmarks to numerical claims so AI agents can accurately parse performance specs.",
            ))

        # -------------------------------------------------------------
        # FQ-04: Ungrounded Superlatives Lacking Citations
        # -------------------------------------------------------------
        superlative_evs: List[Evidence] = []
        for u_url, chunks in text_by_url.items():
            for text, ev_id, loc in chunks:
                for sup_pat in SUPERLATIVE_PATTERNS:
                    match = re.search(sup_pat, text, re.IGNORECASE)
                    if match:
                        # Check if citation/source exists in the same text snippet
                        has_citation = any(re.search(cit, text, re.IGNORECASE) for cit in CITATION_PATTERNS)
                        if not has_citation:
                            matched_word = match.group(0)
                            superlative_evs.append(Evidence(
                                source_url=u_url,
                                evidence_type="ungrounded_superlative",
                                observed={
                                    "evidence_id": ev_id,
                                    "superlative": matched_word,
                                    "snippet": text[:120],
                                },
                                location=loc,
                            ))

        if superlative_evs:
            findings.append(Finding(
                skill="fact-quality-audit",
                check_id="FQ-04",
                title="Ungrounded Superlative Claims Lacking Citation",
                status=FindingStatus.WARNING,
                severity=FindingSeverity.MEDIUM,
                description=f"Found {len(superlative_evs)} ungrounded superlative claim(s) (e.g. '#1', 'best', 'only', 'leading') with no adjacent supporting citation, report, or source reference.",
                evidence=superlative_evs[:5],
                recommendation="Anchor extreme marketing superlatives with explicit third-party awards, research citations, or benchmark data to improve LLM factual credibility.",
            ))

    except Exception as err:
        findings.append(Finding(
            skill="fact-quality-audit",
            check_id="FQ-ERR",
            title="Fact Quality Audit Error",
            status=FindingStatus.ERROR,
            severity=FindingSeverity.HIGH,
            description=f"Fact quality audit encountered an execution error: {str(err)}",
            evidence=[Evidence(source_url="https://example.com", evidence_type="error", observed={"error": str(err)})],
            recommendation="Inspect site content and structure for malformed propositions.",
        ))

    return findings
