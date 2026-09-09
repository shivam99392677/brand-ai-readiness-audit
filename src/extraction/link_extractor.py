"""Links and Downloadable Resources Evidence Extractor.

Extracts HTML anchor links, link classifications (internal/external/same-origin/cross-origin/rel),
and downloadable document resources (PDF, DOCX, XLSX, CSV, ZIP).
This module is strictly factual and does NOT judge link authority or quality.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from src.crawler.url_utils import extract_base_domain, is_same_domain, normalize_url
from src.evidence.models import DocumentEvidence, LinkEvidence
from src.extraction.links import DOCUMENT_EXTENSIONS, LinksFormsHTMLParser, extract_page_links_and_resources, get_document_extension
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class LinkExtractor:
    """Extracts factual link relationships and document downloads."""

    def extract_link_evidence(
        self,
        url: str,
        html_content: Optional[str] = None,
        links: Optional[List[LinkEvidence]] = None,
        documents: Optional[List[DocumentEvidence]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized link and resource evidence items."""
        evidence_items: List[CanonicalEvidence] = []
        base_domain = extract_base_domain(url)
        has_raw_html = bool(html_content and html_content.strip())

        extracted_links: List[LinkEvidence] = []
        extracted_docs: List[DocumentEvidence] = []

        if has_raw_html:
            res = extract_page_links_and_resources(html_content, url=url)
            extracted_links = res["links"]
            extracted_docs = res["documents"]
            source_desc = "raw_html"
            method_desc = "html-parser"
        else:
            extracted_links = links or []
            extracted_docs = documents or []
            source_desc = "crawler.page_evidence"
            method_desc = "direct-field"

        # 1. HTML Anchor Links
        for idx, link in enumerate(extracted_links):
            href = link.href
            rel_str = link.rel or ""
            rel_tokens = [r.strip().lower() for r in rel_str.split()] if rel_str else []

            is_int = link.is_internal if hasattr(link, "is_internal") else is_same_domain(href, base_domain)
            is_same_orig = False
            try:
                p_src = urlparse(url)
                p_tgt = urlparse(href)
                is_same_orig = (p_src.scheme == p_tgt.scheme and p_src.netloc == p_tgt.netloc)
            except Exception:
                pass

            link_data = {
                "source_page": url,
                "target_url": href,
                "anchor_text": link.anchor_text,
                "is_internal": is_int,
                "is_same_origin": is_same_orig,
                "is_cross_origin": not is_same_orig,
                "rel": link.rel,
                "target": link.target,
                "is_nofollow": "nofollow" in rel_tokens,
                "is_ugc": "ugc" in rel_tokens,
                "is_sponsored": "sponsored" in rel_tokens,
                "order_index": idx,
            }

            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.LINK_ITEM,
                    source="html_body",
                    url=url,
                    data=link_data,
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<a href='{href[:60]}'>",
                        context=link.anchor_text[:80] if link.anchor_text else None,
                    ),
                )
            )

        # 2. Downloadable Document Resources
        for d_idx, doc in enumerate(extracted_docs):
            doc_data = {
                "source_page": url,
                "document_url": doc.url,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "anchor_text": doc.anchor_text,
                "order_index": d_idx,
            }
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.DOCUMENT_RESOURCE,
                    source="html_body",
                    url=url,
                    data=doc_data,
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<a href='{doc.url[:60]}'>",
                        context=doc.anchor_text,
                    ),
                )
            )

        return evidence_items
