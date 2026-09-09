"""Document Metadata Evidence Extractor.

Extracts head title, meta description, canonical URL, robots meta tags,
OpenGraph properties, Twitter cards, viewport, charset, and language declarations.
This module strictly owns document metadata and generic <meta> tags.
"""

from typing import Any, Dict, List, Optional
from src.extraction.metadata import MetadataHTMLParser, extract_page_metadata
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class MetadataExtractor:
    """Extracts factual document metadata, OpenGraph tags, Twitter tags, and HTML attributes."""

    def extract_metadata_evidence(
        self,
        url: str,
        html_content: Optional[str] = None,
        title: Optional[str] = None,
        meta_description: Optional[str] = None,
        canonical_url: Optional[str] = None,
        language: Optional[str] = None,
        charset: Optional[str] = None,
        meta_tags: Optional[List[Dict[str, str]]] = None,
        robots_directives: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized metadata evidence items."""
        evidence_items: List[CanonicalEvidence] = []
        has_raw_html = bool(html_content and html_content.strip())

        if has_raw_html:
            meta_dict = extract_page_metadata(html_content, url=url)
            t_val = meta_dict.get("title")
            desc_val = meta_dict.get("meta_description")
            canon_val = meta_dict.get("canonical_url")
            lang_val = meta_dict.get("language")
            charset_val = meta_dict.get("charset")
            raw_meta_tags = meta_dict.get("meta_tags", [])
            source_desc = "raw_html"
            method_desc = "html-parser"
        else:
            t_val = title
            desc_val = meta_description
            canon_val = canonical_url
            lang_val = language
            charset_val = charset
            raw_meta_tags = meta_tags or []
            source_desc = "crawler.page_evidence"
            method_desc = "direct-field"

        # 1. Top-Level Page Metadata Summary
        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.PAGE_METADATA,
                source="html_head",
                url=url,
                data={
                    "title": t_val,
                    "description": desc_val,
                    "canonical_url": canon_val,
                    "language": lang_val,
                    "charset": charset_val,
                    "meta_tag_count": len(raw_meta_tags),
                },
                provenance=Provenance(
                    source=source_desc,
                    extraction_method=method_desc,
                    url=url,
                    location="<head>",
                ),
            )
        )

        # 2. Canonical URL Evidence
        if canon_val:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.CANONICAL_URL,
                    source="html_head",
                    url=url,
                    data={"canonical_url": canon_val},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<link rel='canonical'>",
                    ),
                )
            )

        # 3. Language & Charset Evidence
        if lang_val:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.LANGUAGE_META,
                    source="html_head",
                    url=url,
                    data={"language": lang_val},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<html lang='...'>",
                    ),
                )
            )

        if charset_val:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.CHARSET_META,
                    source="html_head",
                    url=url,
                    data={"charset": charset_val},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<meta charset='...'>",
                    ),
                )
            )

        # 4. OpenGraph, Twitter, Viewport, and Robots Meta Tags
        og_fields: Dict[str, str] = {}
        twitter_fields: Dict[str, str] = {}
        robots_meta_val: Optional[str] = None
        viewport_val: Optional[str] = None

        for m in raw_meta_tags:
            name = m.get("name", "").lower().strip()
            prop = m.get("property", "").lower().strip()
            content = m.get("content", "").strip()

            key = prop or name
            if not key or not content:
                continue

            if key.startswith("og:"):
                og_fields[key] = content
            elif key.startswith("twitter:"):
                twitter_fields[key] = content
            elif key == "robots":
                robots_meta_val = content
            elif key == "viewport":
                viewport_val = content

            # Individual meta tag evidence for traceability
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.META_TAG,
                    source="html_head",
                    url=url,
                    data={"name": key, "content": content, "raw_attributes": m},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<meta {key}='...'>",
                    ),
                )
            )

        if viewport_val:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.VIEWPORT_META,
                    source="html_head",
                    url=url,
                    data={"viewport": viewport_val},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<meta name='viewport'>",
                    ),
                )
            )

        if og_fields:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.OPENGRAPH_META,
                    source="html_head",
                    url=url,
                    data={"fields": og_fields, "count": len(og_fields)},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<meta property='og:*'>",
                    ),
                )
            )

        if twitter_fields:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.TWITTER_META,
                    source="html_head",
                    url=url,
                    data={"fields": twitter_fields, "count": len(twitter_fields)},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<meta name='twitter:*'>",
                    ),
                )
            )

        # 5. Robots directives evidence from HTML / headers
        effective_robots = robots_meta_val or (robots_directives.get("x_robots_tag") if robots_directives else None)
        if effective_robots or (robots_directives and any(robots_directives.values())):
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.ROBOTS_RULE,
                    source="html_head",
                    url=url,
                    data={
                        "meta_robots": robots_meta_val,
                        "directives": robots_directives or {},
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<meta name='robots'>",
                    ),
                )
            )

        return evidence_items
