"""Machine-Readable Special Resources Evidence Extractor.

Extracts evidence for emerging AI machine-readable protocols and developer manifests:
/sitemap.xml, /llms.txt, and /openapi.json.
This module is strictly factual and does NOT judge developer readiness or API completeness.
"""

import json
from typing import Any, Dict, List, Optional
from src.crawler.sitemap import parse_sitemap_xml_details
from src.evidence.models import SitemapEvidence
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class ResourceExtractor:
    """Extracts factual evidence from sitemaps, llms.txt, and openapi.json manifests."""

    def extract_sitemap_evidence(
        self,
        sitemaps: Optional[List[SitemapEvidence]] = None,
        raw_sitemap_xml: Optional[str] = None,
        sitemap_url: str = "",
    ) -> List[CanonicalEvidence]:
        """Extracts normalized sitemap evidence records."""
        evidence_items: List[CanonicalEvidence] = []

        if raw_sitemap_xml and sitemap_url:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.RAW_SITEMAP,
                    source="sitemap_xml",
                    url=sitemap_url,
                    data={"raw_xml": raw_sitemap_xml, "length": len(raw_sitemap_xml)},
                    provenance=Provenance(
                        source="crawler.sitemap_fetch",
                        extraction_method="direct-field",
                        url=sitemap_url,
                        location="/sitemap.xml",
                    ),
                    is_raw=True,
                )
            )
            is_index, child_indices, page_urls, lastmod_map = parse_sitemap_xml_details(raw_sitemap_xml, sitemap_url)
            for p_url in page_urls:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.SITEMAP_ENTRY,
                        source="sitemap_xml",
                        url=p_url,
                        data={
                            "url": p_url,
                            "sitemap_source": sitemap_url,
                            "lastmod": lastmod_map.get(p_url),
                            "is_index_child": False,
                        },
                        provenance=Provenance(
                            source="sitemap_xml",
                            extraction_method="xml-parser",
                            url=sitemap_url,
                            location="<url> > <loc>",
                        ),
                    )
                )
            for c_idx in child_indices:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.SITEMAP_ENTRY,
                        source="sitemap_xml",
                        url=c_idx,
                        data={
                            "child_sitemap_url": c_idx,
                            "parent_sitemap": sitemap_url,
                            "is_index_child": True,
                        },
                        provenance=Provenance(
                            source="sitemap_xml",
                            extraction_method="xml-parser",
                            url=sitemap_url,
                            location="<sitemap> > <loc>",
                        ),
                    )
                )

        if sitemaps:
            for sm in sitemaps:
                for entry in sm.entries:
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.SITEMAP_ENTRY,
                            source="sitemap_xml",
                            url=entry.url,
                            data={
                                "url": entry.url,
                                "sitemap_source": sm.url,
                                "lastmod": entry.lastmod,
                            },
                            provenance=Provenance(
                                source="crawler.sitemap_evidence",
                                extraction_method="direct-field",
                                url=sm.url,
                                location="<url> > <loc>",
                            ),
                        )
                    )

        return evidence_items

    def extract_llmstxt_evidence(
        self,
        url: str,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized llms.txt protocol evidence."""
        evidence_items: List[CanonicalEvidence] = []

        # Raw artifact
        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.RAW_LLMSTXT,
                source="llms_txt",
                url=url,
                data={"raw_content": content, "length": len(content), "status_code": status_code},
                provenance=Provenance(
                    source="http_fetch",
                    extraction_method="direct-field",
                    url=url,
                    location="/llms.txt",
                ),
                is_raw=True,
            )
        )

        # Parse sections if markdown structured
        sections: List[Dict[str, str]] = []
        curr_section_title = "Root"
        curr_lines: List[str] = []

        for line in content.splitlines():
            if line.startswith("#"):
                if curr_lines:
                    sections.append({"title": curr_section_title, "content": "\n".join(curr_lines).strip()})
                    curr_lines = []
                curr_section_title = line.lstrip("#").strip()
            else:
                curr_lines.append(line)
        if curr_lines:
            sections.append({"title": curr_section_title, "content": "\n".join(curr_lines).strip()})

        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.LLMSTXT_RESOURCE,
                source="llms_txt",
                url=url,
                data={
                    "status_code": status_code,
                    "available": status_code == 200,
                    "character_count": len(content),
                    "sections": sections,
                    "section_count": len(sections),
                },
                provenance=Provenance(
                    source="raw_llmstxt",
                    extraction_method="markdown-section-parse",
                    url=url,
                    location="/llms.txt",
                ),
            )
        )

        return evidence_items

    def extract_openapi_evidence(
        self,
        url: str,
        raw_json_content: str,
        status_code: int = 200,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized OpenAPI / REST manifest evidence."""
        evidence_items: List[CanonicalEvidence] = []

        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.RAW_OPENAPI,
                source="openapi_json",
                url=url,
                data={"raw_json": raw_json_content, "length": len(raw_json_content), "status_code": status_code},
                provenance=Provenance(
                    source="http_fetch",
                    extraction_method="direct-field",
                    url=url,
                    location="/openapi.json",
                ),
                is_raw=True,
            )
        )

        try:
            parsed = json.loads(raw_json_content)
            paths = list(parsed.get("paths", {}).keys())
            info = parsed.get("info", {})
            version = parsed.get("openapi") or parsed.get("swagger")

            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.OPENAPI_RESOURCE,
                    source="openapi_json",
                    url=url,
                    data={
                        "version": version,
                        "title": info.get("title"),
                        "paths_count": len(paths),
                        "paths": paths[:50],  # Sample paths
                        "schemas_count": len(parsed.get("components", {}).get("schemas", {})),
                    },
                    provenance=Provenance(
                        source="raw_openapi",
                        extraction_method="json-parse",
                        url=url,
                        location="/openapi.json",
                    ),
                )
            )
        except Exception as err:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.OPENAPI_RESOURCE,
                    source="openapi_json",
                    url=url,
                    data={"error": f"JSON parse error: {str(err)}", "status_code": status_code},
                    provenance=Provenance(
                        source="raw_openapi",
                        extraction_method="json-parse",
                        url=url,
                        location="/openapi.json",
                    ),
                )
            )

        return evidence_items
