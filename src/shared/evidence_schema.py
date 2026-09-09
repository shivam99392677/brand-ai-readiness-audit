"""Canonical Evidence Schema for Brand AI Readiness Audit Extraction Layer.

Defines strictly objective, auditable, and traceable Evidence representations.
This layer contains NO audit findings, scores, or evaluations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class EvidenceType(str, Enum):
    """Canonical classification of extracted factual evidence items."""
    # HTTP / Network
    HTTP_STATUS = "http_status"
    HTTP_REDIRECT = "http_redirect"
    HTTP_HEADER = "http_header"
    RAW_HEADERS = "raw_headers"
    RESPONSE_TIMING = "response_timing"
    HTTP_REQUEST_META = "http_request_meta"

    # Raw Artifacts
    RAW_HTML = "raw_html"
    RENDERED_DOM = "rendered_dom"
    RENDER_ARTIFACT = "render_artifact"
    RAW_ROBOTS = "raw_robots"
    RAW_SITEMAP = "raw_sitemap"
    RAW_LLMSTXT = "raw_llmstxt"
    RAW_OPENAPI = "raw_openapi"

    # Document Metadata
    PAGE_METADATA = "page_metadata"
    CANONICAL_URL = "canonical_url"
    META_TAG = "meta_tag"
    OPENGRAPH_META = "opengraph_meta"
    TWITTER_META = "twitter_meta"
    LANGUAGE_META = "language_meta"
    CHARSET_META = "charset_meta"
    VIEWPORT_META = "viewport_meta"

    # Text & Structural Content
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_BLOCK = "list_block"
    TABLE_BLOCK = "table_block"
    BLOCKQUOTE_BLOCK = "blockquote_block"
    CAPTION_BLOCK = "caption_block"
    FAQ_BLOCK = "faq_block"
    VISIBLE_TEXT_SUMMARY = "visible_text_summary"
    TEXT_EXTRACTABILITY_SIGNAL = "text_extractability_signal"

    # Schema.org & Semantic Markup
    JSONLD_RAW = "jsonld_raw"
    JSONLD_PARSED = "jsonld_parsed"
    SCHEMA_TYPE = "schema_type"
    MICRODATA_ITEM = "microdata_item"

    # Robots.txt
    ROBOTS_RULE = "robots_rule"
    ROBOTS_SITEMAP_DECLARATION = "robots_sitemap_declaration"
    ROBOTS_CRAWL_DELAY = "robots_crawl_delay"
    ROBOTS_PARSE_ERROR = "robots_parse_error"

    # Freshness
    FRESHNESS_DATE = "freshness_date"

    # Entity Identity
    ENTITY_NAME = "entity_name"
    ENTITY_ADDRESS = "entity_address"
    ENTITY_PHONE = "entity_phone"
    ENTITY_EMAIL = "entity_email"
    ENTITY_LOGO = "entity_logo"
    SAME_AS_LINK = "same_as_link"
    WIKIDATA_ID = "wikidata_id"
    ENTITY_IDENTIFIER = "entity_identifier"

    # Links & Resources
    LINK_ITEM = "link_item"
    INTERNAL_LINK = "internal_link"
    EXTERNAL_LINK = "external_link"
    DOCUMENT_RESOURCE = "document_resource"

    # Media & Forms
    IMAGE_ITEM = "image_item"
    FORM_ITEM = "form_item"

    # Machine-Readable Endpoints
    LLMSTXT_RESOURCE = "llmstxt_resource"
    OPENAPI_RESOURCE = "openapi_resource"
    SITEMAP_ENTRY = "sitemap_entry"

    # Sitewide Crawl & Coverage
    CRAWL_COVERAGE = "crawl_coverage"
    CRAWL_RESOURCE_SUMMARY = "crawl_resource_summary"
    FAILED_URL_RECORD = "failed_url_record"
    SKIPPED_URL_RECORD = "skipped_url_record"
    CRAWL_ERROR = "crawl_error"

    # Absence / Negative Signal
    EXTRACTION_ABSENCE = "extraction_absence"


class Provenance(BaseModel):
    """Standardized traceable pointer identifying the origin and extraction method of an evidence item."""
    source: str = Field(..., description="Origin source identifier (e.g., 'crawler.response.headers', 'raw_html', 'jsonld_raw_block')")
    extraction_method: str = Field(default="direct-field", description="Extraction technique (e.g., 'direct-field', 'html-parser', 'json-parse', 'regex-search')")
    url: Optional[str] = Field(default=None, description="URL of the page or endpoint where evidence originated")
    source_url: Optional[str] = Field(default=None, description="Alias for url to preserve backward compatibility")
    location: Optional[str] = Field(default=None, description="DOM element tag, CSS selector, JSON path, or header name")
    selector: Optional[str] = Field(default=None, description="Specific CSS selector or XPath if applicable")
    path: Optional[str] = Field(default=None, description="JSONPath or URL path pointer if applicable")
    line_number: Optional[int] = Field(default=None, description="Optional line number pointer")
    context: Optional[str] = Field(default=None, description="Short surrounding snippet or context string")

    @model_validator(mode="before")
    @classmethod
    def sync_url_and_source_url(cls, values: Any) -> Any:
        if isinstance(values, dict):
            u = values.get("url")
            su = values.get("source_url")
            if not u and su:
                values["url"] = su
            elif not su and u:
                values["source_url"] = u
            if "source" not in values and values.get("source_url"):
                values["source"] = values["source_url"]
        return values


class CanonicalEvidence(BaseModel):
    """Canonical, auditable unit of factual evidence collected from crawl data."""
    id: str = Field(..., description="Globally unique evidence ID within the run, e.g. EV-00001")
    type: Union[EvidenceType, str] = Field(..., description="Canonical evidence category")
    source: str = Field(..., description="High-level source classification (e.g. 'http_response', 'html_body', 'json_ld')")
    url: Optional[str] = Field(default=None, description="Associated page or resource URL")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 extraction timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Objective normalized factual data dictionary")
    provenance: Provenance = Field(..., description="Traceable origin provenance metadata")
    is_raw: bool = Field(default=False, description="True if payload represents an unmodified raw artifact")
    raw_ref: Optional[str] = Field(default=None, description="Reference key or hash to raw payload artifact if stored externally")

    # Property aliases for backward compatibility with audit findings
    @property
    def source_url(self) -> str:
        return self.url or self.provenance.source_url or ""

    @property
    def evidence_type(self) -> str:
        return str(self.type.value if isinstance(self.type, EvidenceType) else self.type)

    @property
    def observed(self) -> Dict[str, Any]:
        return self.data

    @property
    def location(self) -> Optional[str]:
        return self.provenance.location


# Alias for intuitive importing
Evidence = CanonicalEvidence


class ExtractionError(BaseModel):
    """Structured record of an extractor warning or non-fatal failure."""
    extractor: str = Field(..., description="Name of the extractor that encountered the error")
    source: str = Field(..., description="Source URL or context being processed")
    error: str = Field(..., description="Error message or exception description")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional context or stack details")


class ExtractionResult(BaseModel):
    """Top-level container returned by the Extraction Layer."""
    evidence: List[CanonicalEvidence] = Field(default_factory=list, description="Ordered canonical evidence records")
    errors: List[ExtractionError] = Field(default_factory=list, description="Non-fatal extraction errors encountered")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics, counts, and timing")
