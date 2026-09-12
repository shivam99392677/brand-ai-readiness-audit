"""Structured Data Audit Skill Implementation (SD-001 through SD-006)."""

from html.parser import HTMLParser
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.models import (
    Evidence,
    Finding,
    FindingSeverity,
    FindingStatus,
)


class StructuredDataHTMLParser(HTMLParser):
    """HTML Parser for extracting JSON-LD scripts, Microdata, meta tags, and visible title/headings."""

    def __init__(self):
        super().__init__()
        self.jsonld_blocks: List[Tuple[int, str]] = []  # (index, raw_text)
        self.meta_tags: List[Dict[str, str]] = []
        self.microdata_items: List[Dict[str, Any]] = []
        self.title_text: Optional[str] = None
        self.h1_texts: List[str] = []

        self._in_jsonld = False
        self._current_jsonld_text: List[str] = []
        self._current_jsonld_index = 0

        self._in_title = False
        self._title_buffer: List[str] = []

        self._in_h1 = False
        self._h1_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        if tag_lower == "script":
            if attr_dict.get("type", "").strip().lower() == "application/ld+json":
                self._in_jsonld = True
                self._current_jsonld_text = []
                self._current_jsonld_index = len(self.jsonld_blocks)
        elif tag_lower == "meta":
            self.meta_tags.append(attr_dict)
        elif tag_lower == "title":
            self._in_title = True
            self._title_buffer = []
        elif tag_lower == "h1":
            self._in_h1 = True
            self._h1_buffer = []

        if "itemscope" in attr_dict or "itemtype" in attr_dict or "itemprop" in attr_dict:
            self.microdata_items.append({
                "tag": tag_lower,
                "itemscope": "itemscope" in attr_dict,
                "itemtype": attr_dict.get("itemtype", ""),
                "itemprop": attr_dict.get("itemprop", ""),
                "content": attr_dict.get("content", ""),
            })

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "script" and self._in_jsonld:
            raw_text = "".join(self._current_jsonld_text).strip()
            self.jsonld_blocks.append((self._current_jsonld_index, raw_text))
            self._in_jsonld = False
        elif tag_lower == "title" and self._in_title:
            self.title_text = "".join(self._title_buffer).strip()
            self._in_title = False
        elif tag_lower == "h1" and self._in_h1:
            h1_text = "".join(self._h1_buffer).strip()
            if h1_text:
                self.h1_texts.append(h1_text)
            self._in_h1 = False

    def handle_data(self, data: str):
        if self._in_jsonld:
            self._current_jsonld_text.append(data)
        if self._in_title:
            self._title_buffer.append(data)
        if self._in_h1:
            self._h1_buffer.append(data)


def extract_schema_objects(obj: Any) -> List[Dict[str, Any]]:
    """Recursively extracts dictionary objects containing @type or itemtype from nested structures."""
    results: List[Dict[str, Any]] = []
    if isinstance(obj, dict):
        if "@type" in obj or "itemtype" in obj or "type" in obj:
            results.append(obj)
        for key, val in obj.items():
            if key == "@graph" and isinstance(val, list):
                for item in val:
                    results.extend(extract_schema_objects(item))
            elif isinstance(val, (dict, list)):
                results.extend(extract_schema_objects(val))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(extract_schema_objects(item))
    return results


def get_type_names(type_val: Any) -> List[str]:
    """Helper to normalize @type value(s) into a list of strings."""
    if isinstance(type_val, str):
        return [type_val]
    elif isinstance(type_val, list):
        return [str(t) for t in type_val if isinstance(t, str)]
    return []


def sanitize_raw_object(obj: Dict[str, Any], max_len: int = 1000) -> Dict[str, Any]:
    """Truncates large objects for evidence logging while keeping core identifying attributes."""
    dumped = json.dumps(obj)
    if len(dumped) <= max_len:
        return obj

    # Truncated view keeping primary fields
    summary = {}
    for k in ["@context", "@type", "type", "name", "url", "id", "@id", "headline"]:
        if k in obj:
            summary[k] = obj[k]
    summary["_note"] = f"Payload truncated for evidence brevity (original size: {len(dumped)} bytes)"
    return summary


class StructuredDataAuditor:
    """Executes deterministic audit checks SD-001 through SD-006 for structured data."""

    def __init__(self, html_content: str, url: str):
        self.html = html_content
        self.url = url
        self.parser = StructuredDataHTMLParser()
        self.parser.feed(self.html)

        self.parsed_blocks: List[Tuple[int, Optional[Any], Optional[str]]] = []
        for idx, raw_text in self.parser.jsonld_blocks:
            try:
                data = json.loads(raw_text)
                self.parsed_blocks.append((idx, data, None))
            except Exception as err:
                self.parsed_blocks.append((idx, None, str(err)))

    def run_all_checks(self) -> List[Finding]:
        """Executes all structured data audit checks (SD-001 to SD-006)."""
        findings = [
            self.check_sd_001_detection(),
            self.check_sd_002_validity(),
            self.check_sd_003_type_detection(),
            self.check_sd_004_entity_information(),
            self.check_sd_005_visible_consistency(),
            self.check_sd_006_duplicate_conflicts(),
        ]
        return findings

    def check_sd_001_detection(self) -> Finding:
        """SD-001: JSON-LD Detection."""
        block_count = len(self.parser.jsonld_blocks)
        if block_count > 0:
            ev = Evidence(
                source_url=self.url,
                evidence_type="jsonld_detection",
                observed={"detected_count": block_count},
                location=f"script[type='application/ld+json'] (count: {block_count})",
                details={"script_indices": [idx for idx, _ in self.parser.jsonld_blocks]},
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-001",
                title="JSON-LD Script Block Detection",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"Detected {block_count} JSON-LD script block(s) in HTML document.",
                evidence=[ev],
                recommendation="Maintain valid JSON-LD script blocks.",
            )
        else:
            # Also check microdata/opengraph fallback
            meta_og_count = sum(1 for m in self.parser.meta_tags if "property" in m and m["property"].startswith("og:"))
            microdata_count = len(self.parser.microdata_items)

            ev = Evidence(
                source_url=self.url,
                evidence_type="jsonld_detection",
                observed={
                    "detected_jsonld_count": 0,
                    "opengraph_meta_tags": meta_og_count,
                    "microdata_elements": microdata_count,
                },
                expected={"detected_jsonld_count": ">= 1"},
                location="head/body script tags",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-001",
                title="JSON-LD Script Block Detection",
                status=FindingStatus.NOT_APPLICABLE,
                severity=FindingSeverity.INFO,
                description="No JSON-LD script blocks were detected in the HTML document (optional for general/blog pages).",
                evidence=[ev],
                recommendation="Consider adding JSON-LD structured data script blocks for primary entities.",
            )

    def check_sd_002_validity(self) -> Finding:
        """SD-002: JSON-LD Parse Validity."""
        if not self.parser.jsonld_blocks:
            ev = Evidence(
                source_url=self.url,
                evidence_type="jsonld_syntax",
                observed={"jsonld_blocks_present": False},
                location="script[type='application/ld+json']",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-002",
                title="JSON-LD Parse Validity",
                status=FindingStatus.NOT_APPLICABLE,
                severity=FindingSeverity.INFO,
                description="Skipped JSON-LD parse validity check because no JSON-LD script blocks were found.",
                evidence=[ev],
                recommendation="N/A",
            )

        malformed = [(idx, err) for idx, data, err in self.parsed_blocks if err is not None]
        if not malformed:
            ev = Evidence(
                source_url=self.url,
                evidence_type="jsonld_syntax",
                observed={
                    "total_blocks": len(self.parsed_blocks),
                    "valid_blocks": len(self.parsed_blocks),
                    "invalid_blocks": 0,
                },
                location=f"script[type='application/ld+json'][0..{len(self.parsed_blocks)-1}]",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-002",
                title="JSON-LD Parse Validity",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"All {len(self.parsed_blocks)} JSON-LD script block(s) parsed cleanly as valid JSON.",
                evidence=[ev],
                recommendation="Ensure JSON-LD content remains syntactically valid upon site updates.",
            )
        else:
            ev_items = []
            for idx, err in malformed:
                raw_snippet = self.parser.jsonld_blocks[idx][1][:200]
                ev_items.append(Evidence(
                    source_url=self.url,
                    evidence_type="jsonld_syntax",
                    observed={"parse_error": err, "raw_snippet": raw_snippet},
                    location=f"script[type='application/ld+json'][{idx}]",
                ))
            return Finding(
                skill="structured-data-audit",
                check_id="SD-002",
                title="JSON-LD Parse Validity",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                description=f"Found {len(malformed)} malformed JSON-LD script block(s) with JSON syntax errors.",
                evidence=ev_items,
                recommendation="Fix syntax errors (e.g. trailing commas, unescaped quotes) in JSON-LD script blocks.",
            )

    def check_sd_003_type_detection(self) -> Finding:
        """SD-003: Schema Type Detection."""
        detected_types: Set[str] = set()

        for idx, data, err in self.parsed_blocks:
            if data is not None:
                schemas = extract_schema_objects(data)
                for s in schemas:
                    for t in get_type_names(s.get("@type") or s.get("type")):
                        detected_types.add(t)

        # Microdata fallback check
        for m in self.parser.microdata_items:
            if m.get("itemtype"):
                detected_types.add(m["itemtype"].split("/")[-1])

        if detected_types:
            sorted_types = sorted(list(detected_types))
            ev = Evidence(
                source_url=self.url,
                evidence_type="schema_type_detection",
                observed={"detected_schema_types": sorted_types, "count": len(sorted_types)},
                location="JSON-LD @type / Microdata itemtype",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-003",
                title="Schema Type Detection",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"Identified {len(sorted_types)} schema type(s): {', '.join(sorted_types)}.",
                evidence=[ev],
                recommendation="Verify detected schema types conform to Schema.org vocabulary definitions.",
            )
        else:
            ev = Evidence(
                source_url=self.url,
                evidence_type="schema_type_detection",
                observed={"detected_schema_types": []},
                expected={"detected_schema_types": ["Organization", "WebSite", "Product", "etc."]},
                location="JSON-LD @type / Microdata itemtype",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-003",
                title="Schema Type Detection",
                status=FindingStatus.NOT_APPLICABLE,
                severity=FindingSeverity.INFO,
                description="No explicit @type or microdata itemtype declarations were detected on this page (optional for non-product/general pages).",
                evidence=[ev],
                recommendation="Add explicit @type properties to JSON-LD objects where applicable.",
            )

    def check_sd_004_entity_information(self) -> Finding:
        """SD-004: Entity Information Completeness (Organization, Person, Product, WebSite, etc.)."""
        target_entity_types = {"Organization", "Person", "Product", "WebSite", "LocalBusiness", "Article", "FAQPage"}
        extracted_entities: List[Dict[str, Any]] = []

        for idx, data, err in self.parsed_blocks:
            if data is not None:
                schemas = extract_schema_objects(data)
                for s in schemas:
                    types = get_type_names(s.get("@type") or s.get("type"))
                    matched_types = [t for t in types if t in target_entity_types]
                    if matched_types:
                        extracted_entities.append({
                            "matched_types": matched_types,
                            "raw_schema": sanitize_raw_object(s),
                            "name": s.get("name"),
                            "url": s.get("url"),
                            "script_index": idx,
                        })

        if not extracted_entities:
            ev = Evidence(
                source_url=self.url,
                evidence_type="entity_information",
                observed={"target_entities_found": 0},
                location="JSON-LD script blocks",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-004",
                title="Entity Information Completeness",
                status=FindingStatus.NOT_APPLICABLE,
                severity=FindingSeverity.INFO,
                description="No Organization, Person, Product, WebSite, or Article entities were present in structured data.",
                evidence=[ev],
                recommendation="N/A",
            )

        incomplete_entities = []
        complete_entities = []

        for ent in extracted_entities:
            # Check for core missing attributes (e.g. Organization missing name)
            has_name_or_url = bool(ent.get("name") or ent.get("url"))
            if not has_name_or_url:
                incomplete_entities.append(ent)
            else:
                complete_entities.append(ent)

        if not incomplete_entities:
            ev = Evidence(
                source_url=self.url,
                evidence_type="entity_information",
                observed={
                    "entity_count": len(complete_entities),
                    "entities": [
                        {"types": e["matched_types"], "name": e.get("name"), "url": e.get("url")}
                        for e in complete_entities
                    ],
                },
                location="JSON-LD script blocks",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-004",
                title="Entity Information Completeness",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"Extracted entity information for {len(complete_entities)} entity object(s) with core properties.",
                evidence=[ev],
                recommendation="Maintain complete entity property fields across structured data objects.",
            )
        else:
            ev = Evidence(
                source_url=self.url,
                evidence_type="entity_information",
                observed={
                    "incomplete_entity_count": len(incomplete_entities),
                    "incomplete_entities": [
                        {"types": e["matched_types"], "script_index": e["script_index"]}
                        for e in incomplete_entities
                    ],
                },
                expected={"core_properties": ["name", "url"]},
                location="JSON-LD script blocks",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-004",
                title="Entity Information Completeness",
                status=FindingStatus.WARNING,
                severity=FindingSeverity.MEDIUM,
                description=f"Found {len(incomplete_entities)} entity object(s) missing core identifying attributes (name or url).",
                evidence=[ev],
                recommendation="Provide core identifying attributes such as 'name' and 'url' for structured entities.",
            )

    def check_sd_005_visible_consistency(self) -> Finding:
        """SD-005: Consistency between structured data and visible page information."""
        visible_title = self.parser.title_text
        visible_h1 = self.parser.h1_texts[0] if self.parser.h1_texts else None

        sd_names: List[Tuple[str, str]] = []  # (entity_type, name)
        for idx, data, err in self.parsed_blocks:
            if data is not None:
                schemas = extract_schema_objects(data)
                for s in schemas:
                    types = get_type_names(s.get("@type") or s.get("type"))
                    name = s.get("name")
                    if isinstance(name, str) and name.strip():
                        for t in types:
                            sd_names.append((t, name.strip()))

        if not sd_names or (not visible_title and not visible_h1):
            ev = Evidence(
                source_url=self.url,
                evidence_type="visible_consistency",
                observed={
                    "structured_data_names": [n for _, n in sd_names],
                    "visible_title": visible_title,
                    "visible_h1": visible_h1,
                },
                location="<title> / <h1> / JSON-LD name",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-005",
                title="Structured Data vs Visible Content Consistency",
                status=FindingStatus.NOT_APPLICABLE,
                severity=FindingSeverity.INFO,
                description="Insufficient visible page text or structured entity names to verify consistency deterministically.",
                evidence=[ev],
                recommendation="N/A",
            )

        conflicts = []
        matches = []

        visible_tokens = set(re.findall(r"\w+", (visible_title or "") + " " + (visible_h1 or "")))
        visible_tokens_lower = {t.lower() for t in visible_tokens}

        for ent_type, sd_name in sd_names:
            sd_tokens = set(re.findall(r"\w+", sd_name))
            sd_tokens_lower = {t.lower() for t in sd_tokens}

            # Check if there is meaningful overlap or matching tokens
            if sd_tokens_lower and visible_tokens_lower:
                overlap = sd_tokens_lower.intersection(visible_tokens_lower)
                # If zero token overlap between a multi-word entity name and visible text, flag potential conflict
                if len(sd_tokens_lower) > 1 and not overlap:
                    conflicts.append((ent_type, sd_name))
                else:
                    matches.append((ent_type, sd_name))

        if conflicts:
            ev = Evidence(
                source_url=self.url,
                evidence_type="visible_consistency",
                observed={
                    "conflicting_entities": [{"type": t, "sd_name": n} for t, n in conflicts],
                    "visible_title": visible_title,
                    "visible_h1": visible_h1,
                },
                expected={"text_alignment": "Structured data entity name should align with page title or heading"},
                location="<title> / <h1> vs JSON-LD name",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-005",
                title="Structured Data vs Visible Content Consistency",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.HIGH,
                description=f"Detected discrepancy between structured entity names ({[n for _, n in conflicts]}) and visible page title/h1.",
                evidence=[ev],
                recommendation="Align structured data entity names with visible page headings and page titles.",
            )
        else:
            ev = Evidence(
                source_url=self.url,
                evidence_type="visible_consistency",
                observed={
                    "matched_entities": [{"type": t, "sd_name": n} for t, n in matches],
                    "visible_title": visible_title,
                    "visible_h1": visible_h1,
                },
                location="<title> / <h1> vs JSON-LD name",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-005",
                title="Structured Data vs Visible Content Consistency",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description="Structured data entity names align deterministically with visible page title/heading text.",
                evidence=[ev],
                recommendation="Maintain consistent branding between visible page elements and structured markup.",
            )

    def check_sd_006_duplicate_conflicts(self) -> Finding:
        """SD-006: Duplicate/conflicting structured data where detectable."""
        entities_by_type: Dict[str, List[Dict[str, Any]]] = {}

        for idx, data, err in self.parsed_blocks:
            if data is not None:
                schemas = extract_schema_objects(data)
                for s in schemas:
                    types = get_type_names(s.get("@type") or s.get("type"))
                    for t in types:
                        entities_by_type.setdefault(t, []).append(s)

        conflicting_types: Dict[str, List[str]] = {}

        for t, items in entities_by_type.items():
            if len(items) > 1:
                # Compare canonical 'name' or 'url' fields across instances of the same schema type
                names = set()
                for item in items:
                    n = item.get("name")
                    if isinstance(n, str) and n.strip():
                        names.add(n.strip().lower())

                # If multiple distinct names exist for the same entity type (e.g. two conflicting Organizations)
                if len(names) > 1:
                    conflicting_types[t] = list(names)

        if conflicting_types:
            ev = Evidence(
                source_url=self.url,
                evidence_type="duplicate_conflict",
                observed={"conflicting_types": conflicting_types},
                expected={"single_canonical_name": "Multiple entities of the same type should not declare conflicting names"},
                location="Multiple script[type='application/ld+json'] blocks",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-006",
                title="Duplicate or Conflicting Structured Data",
                status=FindingStatus.FAIL,
                severity=FindingSeverity.MEDIUM,
                description=f"Detected conflicting property values across duplicate schema declarations for type(s): {', '.join(conflicting_types.keys())}.",
                evidence=[ev],
                recommendation="Consolidate duplicate schema declarations into a single canonical entity object.",
            )
        else:
            ev = Evidence(
                source_url=self.url,
                evidence_type="duplicate_conflict",
                observed={"detected_entity_types_count": len(entities_by_type)},
                location="JSON-LD script blocks",
            )
            return Finding(
                skill="structured-data-audit",
                check_id="SD-006",
                title="Duplicate or Conflicting Structured Data",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description="No conflicting structured data declarations were detected across schema objects.",
                evidence=[ev],
                recommendation="Maintain unique canonical declarations for primary brand entities.",
            )


def audit_structured_data(html_content: str, url: str) -> List[Finding]:
    """Helper function to execute structured data audit checks on HTML string content."""
    auditor = StructuredDataAuditor(html_content=html_content, url=url)
    return auditor.run_all_checks()


def run_structured_data_audit(
    evidence: Any,
    website: Optional[Any] = None,
    html_content: Optional[str] = None,
    url: Optional[str] = None,
    **kwargs,
) -> List[Finding]:
    """Canonical entrypoint for structured data audit skill consuming ExtractionResult & WebsiteEvidence."""
    findings: List[Finding] = []
    
    # 1. Direct HTML fallback for backward compatibility
    if html_content is not None and url is not None:
        return audit_structured_data(html_content=html_content, url=url)
    
    # 2. Extract from WebsiteEvidence pages if provided
    pages_to_audit = []
    if website is not None and hasattr(website, "pages") and website.pages:
        pages_to_audit = website.pages
    elif hasattr(evidence, "evidence"):
        # Find raw HTML or unique page URLs from ExtractionResult
        raw_html_evs = [e for e in evidence.evidence if e.type == "raw_html" and e.data.get("html_content")]
        for rhe in raw_html_evs:
            pages_to_audit.append(type("DummyPage", (), {"url": rhe.url, "html_content": rhe.data.get("html_content"), "page_role": "unknown"})())

    if not pages_to_audit:
        target_u = getattr(website, "start_url", "https://example.com") if website else "https://example.com"
        return [Finding(
            skill="structured-data-audit",
            check_id="SD-001",
            title="JSON-LD Schema Verification",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="No crawlable HTML pages required schema evaluation.",
            evidence=[Evidence(source_url=target_u, evidence_type="schema_info", observed={"status": "no_pages"})],
            recommendation="Add Schema.org JSON-LD to primary brand and product pages.",
        )]

    for page in pages_to_audit[:10]:  # Audit up to 10 representative pages
        p_html = getattr(page, "html_content", None) or ""
        p_url = getattr(page, "url", "https://example.com")
        p_role = getattr(page, "page_role", "unknown")

        if p_html:
            auditor = StructuredDataAuditor(html_content=p_html, url=p_url)
            page_findings = auditor.run_all_checks()

            for f in page_findings:
                # Rule: Never report "no schema on site" as a defect for non-product/general pages
                if f.check_id == "SD-001" and f.status in (FindingStatus.WARNING, FindingStatus.FAIL):
                    if p_role not in ("product", "pricing") and "product" not in p_url.lower():
                        # Soften to INFO / PASS so it does not appear as a defect
                        f.status = FindingStatus.PASS
                        f.severity = FindingSeverity.INFO
                        f.description = "Informational: Non-product page contains no JSON-LD schema (optional)."
                findings.append(f)

    return findings
