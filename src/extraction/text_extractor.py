"""Text and Content Evidence Extractor.

Extracts structured text blocks (headings, paragraphs, lists, tables, blockquotes, captions),
text length metrics, and word-boundary collapse signals.
This module is strictly factual and does NOT evaluate content quality, tone, or readability.
"""

from typing import Any, Dict, List, Optional
from src.analysis.crawl_render_audit import detect_word_boundary_collapse
from src.extraction.page import GeneralPageHTMLParser, extract_page_content
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class TextExtractor:
    """Extracts structured text blocks, headings hierarchy, and text extractability signals."""

    def extract_text_evidence(
        self,
        url: str,
        html_content: Optional[str] = None,
        headings: Optional[List[Dict[str, str]]] = None,
        paragraphs: Optional[List[str]] = None,
        lists: Optional[List[List[str]]] = None,
        tables: Optional[List[Dict[str, Any]]] = None,
        blockquotes: Optional[List[str]] = None,
        captions: Optional[List[str]] = None,
        word_count: Optional[int] = None,
        raw_text_length: Optional[int] = None,
        normalized_text_length: Optional[int] = None,
        text_extractability: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts factual structured text evidence items."""
        evidence_items: List[CanonicalEvidence] = []

        parsed_content: Optional[Dict[str, Any]] = None
        has_raw_html = bool(html_content and html_content.strip())

        if has_raw_html:
            parsed_content = extract_page_content(html_content, url=url)
            h_list = parsed_content["headings"]
            p_list = parsed_content["paragraphs"]
            l_list = parsed_content["lists"]
            t_list = parsed_content["tables"]
            bq_list = parsed_content["blockquotes"]
            cap_list = parsed_content["captions"]
            wc = parsed_content["word_count"]
            norm_text = parsed_content["normalized_text"]
            raw_len = len(parsed_content["raw_text"])
            norm_len = len(norm_text)
            collapsed, suspicious_toks = detect_word_boundary_collapse(norm_text)
            ext_metrics = {
                "word_boundary_collapse_detected": collapsed,
                "suspicious_tokens": suspicious_toks,
                "raw_text_length": raw_len,
                "normalized_text_length": norm_len,
            }
            source_desc = "raw_html"
            method_desc = "html-parser"
        else:
            h_list = headings or []
            p_list = paragraphs or []
            l_list = lists or []
            t_list = tables or []
            bq_list = blockquotes or []
            cap_list = captions or []
            wc = word_count or 0
            raw_len = raw_text_length or 0
            norm_len = normalized_text_length or 0
            ext_metrics = text_extractability or {}
            source_desc = "crawler.page_evidence"
            method_desc = "direct-field"

        # 1. Headings Hierarchy Evidence
        for idx, h in enumerate(h_list):
            tag = h.get("tag", "h1").lower()
            level = int(tag[1]) if len(tag) == 2 and tag[1].isdigit() else 1
            h_text = h.get("text", "").strip()
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.HEADING,
                    source="html_body",
                    url=url,
                    data={
                        "tag": tag,
                        "level": level,
                        "text": h_text,
                        "order_index": idx,
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<{tag}>",
                        context=h_text[:100],
                    ),
                )
            )

        # 2. Paragraphs Evidence
        for idx, p_text in enumerate(p_list):
            clean_p = p_text.strip()
            if clean_p:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.PARAGRAPH,
                        source="html_body",
                        url=url,
                        data={
                            "text": clean_p,
                            "order_index": idx,
                            "character_length": len(clean_p),
                            "word_count": len(clean_p.split()),
                        },
                        provenance=Provenance(
                            source=source_desc,
                            extraction_method=method_desc,
                            url=url,
                            location="<p>",
                            context=clean_p[:100],
                        ),
                    )
                )

        # 3. Lists Evidence
        for idx, l_items in enumerate(l_list):
            if l_items:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.LIST_BLOCK,
                        source="html_body",
                        url=url,
                        data={
                            "items": l_items,
                            "item_count": len(l_items),
                            "order_index": idx,
                        },
                        provenance=Provenance(
                            source=source_desc,
                            extraction_method=method_desc,
                            url=url,
                            location="<ul>|<ol>",
                        ),
                    )
                )

        # 4. Tables Evidence
        for idx, t_obj in enumerate(t_list):
            rows = t_obj.get("rows", []) if isinstance(t_obj, dict) else t_obj
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.TABLE_BLOCK,
                    source="html_body",
                    url=url,
                    data={
                        "rows": rows,
                        "row_count": len(rows),
                        "order_index": idx,
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location="<table>",
                    ),
                )
            )

        # 5. Blockquotes Evidence
        for idx, bq_text in enumerate(bq_list):
            clean_bq = bq_text.strip()
            if clean_bq:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.BLOCKQUOTE_BLOCK,
                        source="html_body",
                        url=url,
                        data={
                            "text": clean_bq,
                            "order_index": idx,
                        },
                        provenance=Provenance(
                            source=source_desc,
                            extraction_method=method_desc,
                            url=url,
                            location="<blockquote>",
                            context=clean_bq[:100],
                        ),
                    )
                )

        # 6. Captions Evidence
        for idx, cap_text in enumerate(cap_list):
            clean_cap = cap_text.strip()
            if clean_cap:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.CAPTION_BLOCK,
                        source="html_body",
                        url=url,
                        data={
                            "text": clean_cap,
                            "order_index": idx,
                        },
                        provenance=Provenance(
                            source=source_desc,
                            extraction_method=method_desc,
                            url=url,
                            location="<figcaption>|<caption>",
                            context=clean_cap[:100],
                        ),
                    )
                )

        # 7. Visible Text Summary Evidence
        sections = parsed_content.get("sections_found", []) if parsed_content else []
        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.VISIBLE_TEXT_SUMMARY,
                source="html_body",
                url=url,
                data={
                    "word_count": wc,
                    "raw_text_length": raw_len,
                    "normalized_text_length": norm_len,
                    "headings_count": len(h_list),
                    "paragraphs_count": len(p_list),
                    "lists_count": len(l_list),
                    "tables_count": len(t_list),
                    "semantic_sections": sections,
                },
                provenance=Provenance(
                    source=source_desc,
                    extraction_method=method_desc,
                    url=url,
                    location="<body>",
                ),
            )
        )

        # 8. Text Extractability Signal Evidence
        if ext_metrics:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.TEXT_EXTRACTABILITY_SIGNAL,
                    source="html_body",
                    url=url,
                    data={
                        "word_boundary_collapse_detected": ext_metrics.get("word_boundary_collapse_detected", False),
                        "suspicious_tokens": ext_metrics.get("suspicious_tokens", []),
                        "raw_text_length": ext_metrics.get("raw_text_length", raw_len),
                        "normalized_text_length": ext_metrics.get("normalized_text_length", norm_len),
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method="heuristic-analysis",
                        url=url,
                        location="<body> > text()",
                    ),
                )
            )

        return evidence_items
