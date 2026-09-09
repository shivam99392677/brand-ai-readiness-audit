"""Structured Data Evidence Extractor.

Extracts raw JSON-LD script blocks, parsed JSON-LD payloads, discovered Schema.org @types,
Microdata items, and JSON parse errors.
This module strictly owns semantic markup (JSON-LD and Microdata).
"""

import json
from typing import Any, Dict, List, Optional, Set
from src.extraction.structured_data import (
    StructuredDataHTMLParser,
    extract_schema_objects,
    extract_structured_data,
    get_type_names,
)
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class SchemaExtractor:
    """Extracts raw JSON-LD payloads, parsed schema representations, and Microdata elements."""

    def extract_schema_evidence(
        self,
        url: str,
        html_content: Optional[str] = None,
        jsonld_raw_blocks: Optional[List[str]] = None,
        structured_data_summary: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized schema and structured data evidence items."""
        evidence_items: List[CanonicalEvidence] = []
        has_raw_html = bool(html_content and html_content.strip())

        raw_blocks: List[str] = []
        microdata_items: List[Dict[str, Any]] = []
        source_desc = "raw_html" if has_raw_html else "crawler.page_evidence"
        method_desc = "html-parser" if has_raw_html else "direct-field"

        if has_raw_html:
            parser = StructuredDataHTMLParser()
            try:
                parser.feed(html_content)
            except Exception:
                pass
            raw_blocks = parser.jsonld_blocks
            microdata_items = parser.microdata_items
        else:
            raw_blocks = jsonld_raw_blocks or []
            if structured_data_summary and "raw_blocks" in structured_data_summary:
                raw_blocks = structured_data_summary["raw_blocks"]

        detected_types: Set[str] = set()

        # 1. Process JSON-LD Raw Blocks & Parsed Objects
        for idx, raw_json_str in enumerate(raw_blocks):
            # 1a. Raw JSON-LD Block Evidence
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.JSONLD_RAW,
                    source="json_ld",
                    url=url,
                    data={
                        "block_index": idx,
                        "raw_json": raw_json_str,
                        "length": len(raw_json_str),
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method="script-extraction",
                        url=url,
                        location=f"script[type='application/ld+json']:nth-of-type({idx + 1})",
                    ),
                    is_raw=True,
                )
            )

            # 1b. Parsed JSON-LD Evidence & Syntax Error Handling
            try:
                parsed_obj = json.loads(raw_json_str)
                schema_objects = extract_schema_objects(parsed_obj)

                block_types: List[str] = []
                for s in schema_objects:
                    for t in get_type_names(s.get("@type") or s.get("type")):
                        detected_types.add(t)
                        block_types.append(t)

                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.JSONLD_PARSED,
                        source="json_ld",
                        url=url,
                        data={
                            "block_index": idx,
                            "parsed_payload": parsed_obj,
                            "schema_types_in_block": sorted(list(set(block_types))),
                            "schema_objects_count": len(schema_objects),
                        },
                        provenance=Provenance(
                            source="jsonld_raw_block",
                            extraction_method="json-parse",
                            url=url,
                            location=f"script[type='application/ld+json']:nth-of-type({idx + 1})",
                        ),
                    )
                )

                # Individual Schema Object Evidence for top-level entities
                for s_idx, schema_dict in enumerate(schema_objects):
                    types = get_type_names(schema_dict.get("@type") or schema_dict.get("type"))
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.SCHEMA_TYPE,
                            source="json_ld",
                            url=url,
                            data={
                                "types": types,
                                "schema_data": schema_dict,
                                "block_index": idx,
                                "schema_index": s_idx,
                            },
                            provenance=Provenance(
                                source="jsonld_parsed",
                                extraction_method="schema-object-traversal",
                                url=url,
                                location=f"schema_object:{idx}:{s_idx}",
                            ),
                        )
                    )

            except Exception as parse_err:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.ROBOTS_PARSE_ERROR if False else "schema_parse_error",
                        source="json_ld",
                        url=url,
                        data={
                            "block_index": idx,
                            "error": str(parse_err),
                            "raw_snippet": raw_json_str[:200],
                        },
                        provenance=Provenance(
                            source="jsonld_raw_block",
                            extraction_method="json-parse",
                            url=url,
                            location=f"script[type='application/ld+json']:nth-of-type({idx + 1})",
                        ),
                    )
                )

        # 2. Process Microdata Items
        for m_idx, m_item in enumerate(microdata_items):
            item_type = m_item.get("itemtype", "")
            if item_type:
                detected_types.add(item_type.split("/")[-1])

            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.MICRODATA_ITEM,
                    source="microdata",
                    url=url,
                    data={
                        "index": m_idx,
                        "tag": m_item.get("tag"),
                        "itemtype": item_type,
                        "itemprop": m_item.get("itemprop"),
                        "itemscope": m_item.get("itemscope", False),
                        "content": m_item.get("content"),
                    },
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<{m_item.get('tag')} itemscope/itemprop>",
                    ),
                )
            )

        # 3. Fallback to summary detected types if no raw blocks available
        if not raw_blocks and structured_data_summary:
            summary_types = structured_data_summary.get("detected_types", [])
            for st in summary_types:
                detected_types.add(st)
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.SCHEMA_TYPE,
                        source="crawler_summary",
                        url=url,
                        data={"types": [st], "source": "crawler_summary"},
                        provenance=Provenance(
                            source="crawler.structured_data.summary",
                            extraction_method="direct-field",
                            url=url,
                            location="summary:detected_types",
                        ),
                    )
                )

        return evidence_items
