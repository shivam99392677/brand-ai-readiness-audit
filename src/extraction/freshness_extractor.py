"""Freshness and Temporal Evidence Extractor.

Extracts publication and modification timestamps across HTTP headers (Last-Modified),
JSON-LD properties (datePublished, dateModified), Sitemap entries (<lastmod>),
meta tags (article:modified_time), and visible DOM dates.
This module is strictly factual and does NOT judge staleness or content recency.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from src.crawler.robots import parse_robots_txt_rules
from src.evidence.models import DateEvidence
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance

DATE_PROP_NAMES = [
    "datepublished",
    "datemodified",
    "datecreated",
    "uploaddate",
    "validfrom",
    "validthrough",
    "expires",
]

META_DATE_KEYS = [
    "article:published_time",
    "article:modified_time",
    "og:updated_time",
    "date",
    "pubdate",
    "dc.date",
    "dc.date.issued",
    "dc.date.modified",
    "last-modified",
]


def try_normalize_date(date_str: str) -> Optional[str]:
    """Attempts to normalize various date string formats into standard ISO 8601 (YYYY-MM-DD or full ISO)."""
    if not date_str:
        return None
    cleaned = date_str.strip()

    # Try standard ISO formats first
    iso_patterns = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]

    for fmt in iso_patterns:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    # Try regex extraction for YYYY-MM-DD
    match = re.search(r"\b(19|20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b", cleaned)
    if match:
        parts = match.group(0).replace("/", "-").replace(".", "-").split("-")
        return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

    return cleaned


class FreshnessExtractor:
    """Extracts temporal date signals with standardized normalization and raw preservation."""

    def extract_freshness_evidence(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        jsonld_objects: Optional[List[Dict[str, Any]]] = None,
        meta_tags: Optional[List[Dict[str, str]]] = None,
        visible_dates: Optional[List[str]] = None,
        sitemap_lastmod: Optional[str] = None,
        date_evidence: Optional[DateEvidence] = None,
        paragraphs: Optional[List[str]] = None,
        html_content: Optional[str] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized date evidence items from all available sources."""
        evidence_items: List[CanonicalEvidence] = []
        raw_headers = headers or {}
        normalized_headers = {k.lower().strip(): v.strip() for k, v in raw_headers.items()}

        # 1. HTTP Last-Modified Header
        if "last-modified" in normalized_headers:
            raw_lm = normalized_headers["last-modified"]
            norm_lm = try_normalize_date(raw_lm)
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.FRESHNESS_DATE,
                    source="http_header",
                    url=url,
                    data={
                        "kind": "last_modified_header",
                        "raw_value": raw_lm,
                        "normalized_value": norm_lm,
                        "source_type": "http_header",
                    },
                    provenance=Provenance(
                        source="crawler.response.headers",
                        extraction_method="header-inspection",
                        url=url,
                        location="header:last-modified",
                    ),
                )
            )

        # 2. Sitemap <lastmod>
        if sitemap_lastmod:
            norm_sm = try_normalize_date(sitemap_lastmod)
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.FRESHNESS_DATE,
                    source="sitemap_xml",
                    url=url,
                    data={
                        "kind": "sitemap_lastmod",
                        "raw_value": sitemap_lastmod,
                        "normalized_value": norm_sm,
                        "source_type": "sitemap_xml",
                    },
                    provenance=Provenance(
                        source="crawler.sitemap.lastmod",
                        extraction_method="xml-parser",
                        url=url,
                        location="<url> > <lastmod>",
                    ),
                )
            )

        # 3. JSON-LD Date Properties (datePublished, dateModified, etc.)
        def extract_jsonld_dates(obj: Any, current_path: str = "$"):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    k_lower = k.lower().replace("@", "")
                    prop_path = f"{current_path}.{k}"
                    if k_lower in DATE_PROP_NAMES and isinstance(v, str) and v.strip():
                        raw_v = v.strip()
                        norm_v = try_normalize_date(raw_v)
                        evidence_items.append(
                            CanonicalEvidence(
                                id="",
                                type=EvidenceType.FRESHNESS_DATE,
                                source="json_ld",
                                url=url,
                                data={
                                    "kind": k,
                                    "raw_value": raw_v,
                                    "normalized_value": norm_v,
                                    "source_type": "jsonld_property",
                                    "property_path": prop_path,
                                },
                                provenance=Provenance(
                                    source="jsonld_parsed",
                                    extraction_method="json-traversal",
                                    url=url,
                                    path=prop_path,
                                    location=f"JSON-LD:{k}",
                                ),
                            )
                        )
                    elif isinstance(v, (dict, list)):
                        extract_jsonld_dates(v, prop_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    extract_jsonld_dates(item, f"{current_path}[{idx}]")

        if jsonld_objects:
            for b_idx, block_obj in enumerate(jsonld_objects):
                extract_jsonld_dates(block_obj, f"$[block_{b_idx}]")

        # 4. Meta Tag Dates
        if meta_tags:
            for m in meta_tags:
                prop = (m.get("property") or m.get("name") or "").lower().strip()
                content = m.get("content", "").strip()
                if prop in META_DATE_KEYS and content:
                    norm_meta_date = try_normalize_date(content)
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.FRESHNESS_DATE,
                            source="html_head",
                            url=url,
                            data={
                                "kind": prop,
                                "raw_value": content,
                                "normalized_value": norm_meta_date,
                                "source_type": "meta_tag",
                            },
                            provenance=Provenance(
                                source="raw_html",
                                extraction_method="html-parser",
                                url=url,
                                location=f"<meta property='{prop}'>",
                            ),
                        )
                    )

        # 5. Visible Text Dates & Footer Copyrights
        vis_dates: List[Tuple[str, str]] = []  # [(kind, date_str)]
        if visible_dates:
            for vd in visible_dates:
                vis_dates.append(("visible_date", vd))
        elif date_evidence and date_evidence.visible_dates:
            for vd in date_evidence.visible_dates:
                vis_dates.append(("visible_date", vd))

        # Scan paragraphs / html text
        text_corpus = list(paragraphs or [])
        if html_content:
            text_corpus.append(html_content)

        date_patterns = [
            (r"\b(?:last\s+updated|updated\s+on|modified\s+on|published\s+on|dated?)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+[12]\d{3}|\d{1,2}[-/.][A-Za-z0-9]+[-/.][12]\d{3}|[12]\d{3}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01]))\b", "visible_date"),
            (r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+[12]\d{3}\b", "visible_date"),
            (r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[12]\d{3}\b", "visible_date"),
            (r"(?:copyright|©|\(c\))\s*(?:[12]\d{3}\s*[-–]\s*)?([12]\d{3})", "footer_copyright"),
        ]

        for p_str in text_corpus:
            for pat, kind in date_patterns:
                matches = re.finditer(pat, p_str, re.IGNORECASE)
                for m in matches:
                    d_val = m.group(1) if m.groups() else m.group(0)
                    vis_dates.append((kind, d_val))

        seen_dates = set()
        for kind, raw_vd in vis_dates:
            clean_vd = raw_vd.strip()
            if clean_vd and (kind, clean_vd) not in seen_dates:
                seen_dates.add((kind, clean_vd))
                norm_vd = try_normalize_date(clean_vd)
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.FRESHNESS_DATE,
                        source="html_body",
                        url=url,
                        data={
                            "kind": kind,
                            "raw_value": clean_vd,
                            "normalized_value": norm_vd,
                            "source_type": kind,
                        },
                        provenance=Provenance(
                            source="raw_html",
                            extraction_method="regex-search",
                            url=url,
                            location="<body> > text()",
                            context=clean_vd,
                        ),
                    )
                )

        return evidence_items
