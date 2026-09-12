"""Shared Evidence Domain Models for Brand AI Readiness Audit.

Defines site-agnostic, objective evidence representations with traceable provenance.
All models are strictly factual and evaluation-free.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class Provenance(BaseModel):
    """Traceable provenance pointer for an extracted evidence item."""
    source_url: str = Field(..., description="URL of the page where evidence was observed")
    location: Optional[str] = Field(default=None, description="DOM selector, HTML element tag, JSON path, or header name")
    line_number: Optional[int] = Field(default=None, description="Optional line number pointer if available")
    context: Optional[str] = Field(default=None, description="Short surrounding text context or snippet")


class UserAgentRuleGroup(BaseModel):
    """Parsed rules for a specific User-Agent group in robots.txt."""
    user_agents: List[str] = Field(default_factory=list, description="Target User-Agent pattern list (e.g. ['*'], ['GPTBot', 'CCBot'])")
    allow: List[str] = Field(default_factory=list, description="Explicitly allowed path patterns")
    disallow: List[str] = Field(default_factory=list, description="Disallowed path patterns")
    crawl_delay: Optional[float] = Field(default=None, description="Specified crawl delay in seconds")

    # Backward compatibility helpers
    @property
    def user_agent(self) -> str:
        return ", ".join(self.user_agents) if self.user_agents else "*"

    @property
    def allow_rules(self) -> List[str]:
        return self.allow

    @property
    def disallow_rules(self) -> List[str]:
        return self.disallow


class RobotsEvidence(BaseModel):
    """Structured observable evidence gathered from robots.txt."""
    url: str = Field(default="", description="Target robots.txt URL")
    available: bool = Field(default=False, description="True if robots.txt returned HTTP 200")
    status_code: int = Field(default=0, description="HTTP response status code")
    user_agent_groups: List[UserAgentRuleGroup] = Field(default_factory=list, description="Per-user-agent rule blocks")
    sitemaps_declared: List[str] = Field(default_factory=list, description="Sitemap URLs declared in robots.txt")
    parse_errors: List[str] = Field(default_factory=list, description="Robots parsing warnings or syntax errors")

    @model_validator(mode="before")
    @classmethod
    def map_robots_legacy_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "robots_url" in values and ("url" not in values or not values["url"]):
                values["url"] = values["robots_url"]
            if "exists" in values and "available" not in values:
                values["available"] = values["exists"]
            if "sitemap_declarations" in values and "sitemaps_declared" not in values:
                values["sitemaps_declared"] = values["sitemap_declarations"]
            if "parsing_errors" in values and "parse_errors" not in values:
                values["parse_errors"] = values["parsing_errors"]
        return values

    # Backward compatibility properties
    @property
    def robots_url(self) -> str:
        return self.url

    @property
    def exists(self) -> bool:
        return self.available

    @property
    def sitemap_declarations(self) -> List[str]:
        return self.sitemaps_declared

    @property
    def parsing_errors(self) -> List[str]:
        return self.parse_errors

    @property
    def allow_rules(self) -> List[str]:
        all_a: List[str] = []
        for g in self.user_agent_groups:
            all_a.extend(g.allow)
        return list(set(all_a))

    @property
    def disallow_rules(self) -> List[str]:
        all_d: List[str] = []
        for g in self.user_agent_groups:
            all_d.extend(g.disallow)
        return list(set(all_d))

    @property
    def crawl_delay(self) -> Optional[float]:
        for g in self.user_agent_groups:
            if g.crawl_delay is not None:
                return g.crawl_delay
        return None


class SitemapEntry(BaseModel):
    """Single URL entry extracted from a sitemap XML."""
    url: str = Field(..., description="Target page URL declared in sitemap")
    lastmod: Optional[str] = Field(default=None, description="Last modified timestamp string if declared")


class SitemapEvidence(BaseModel):
    """Structured observable evidence gathered from sitemap XML/indices."""
    url: str = Field(..., description="Sitemap XML URL")
    available: bool = Field(default=False, description="Availability flag")
    status_code: int = Field(default=0, description="HTTP status code")
    type: str = Field(default="urlset", description="Sitemap type ('urlset' or 'sitemapindex')")
    entries: List[SitemapEntry] = Field(default_factory=list, description="Target page URL entries")
    urls_discovered: List[str] = Field(default_factory=list, description="Discovered target page URLs")
    sitemap_indices: List[str] = Field(default_factory=list, description="Child sitemap URLs if sitemapindex")
    parse_errors: List[str] = Field(default_factory=list, description="Sitemap XML parsing errors")

    # Backward compatibility properties
    @property
    def sitemap_url(self) -> str:
        return self.url

    @property
    def exists(self) -> bool:
        return self.status_code == 200

    @property
    def is_index(self) -> bool:
        return self.type == "sitemapindex"

    @property
    def discovered_urls(self) -> List[str]:
        return [e.url for e in self.entries]

    @property
    def lastmod_map(self) -> Dict[str, str]:
        return {e.url: e.lastmod for e in self.entries if e.lastmod}


class DiscoveredURLEvidence(BaseModel):
    """Traceable evidence for a discovered URL during crawl."""
    url: str = Field(..., description="Discovered target URL")
    discovered_from: Optional[str] = Field(default=None, description="Source page URL where link was found")
    anchor_text: Optional[str] = Field(default=None, description="Anchor text if discovered via HTML link")
    discovery_method: str = Field(default="html_link", description="Discovery method ('html_link', 'sitemap', 'robots_sitemap', 'start_url', 'browser_rendered_link')")
    depth: int = Field(default=0, ge=0, description="Discovered depth level")
    priority: float = Field(default=0.5, description="URL priority score")
    provenance: Optional[Provenance] = Field(default=None, description="Source location pointer")


class FailedURLEvidence(BaseModel):
    """Traceable evidence for a URL that failed during crawl."""
    url: str = Field(..., description="Target URL that failed")
    status_code: int = Field(default=0, description="HTTP status code")
    error_reason: str = Field(default="", description="Error description or exception message")
    discovered_from: Optional[str] = Field(default=None, description="Source page URL")
    anchor_text: Optional[str] = Field(default=None, description="Anchor text if applicable")
    discovery_method: str = Field(default="html_link", description="Discovery method")
    provenance: Optional[Provenance] = Field(default=None, description="Source location pointer")


class ImageEvidence(BaseModel):
    """Generalized factual evidence for a discovered website image asset."""
    declared_url: str = Field(default="", description="Exact original string in HTML/meta attribute")
    resolved_url: str = Field(default="", description="Resolved absolute URL")
    url: str = Field(default="", description="Primary image URL (resolved_url)")
    source_page: str = Field(..., description="Source page URL where image was discovered")
    source_type: str = Field(default="img", description="Source type ('img', 'picture', 'source', 'og_image', 'twitter_image', 'css_background')")
    alt: Optional[str] = Field(default=None, description="Alt attribute text")
    title: Optional[str] = Field(default=None, description="Title attribute text")
    declared_width: Optional[int] = Field(default=None, description="Width attribute declared in HTML")
    declared_height: Optional[int] = Field(default=None, description="Height attribute declared in HTML")
    intrinsic_width: Optional[int] = Field(default=None, description="Actual intrinsic width if fetched (null by default)")
    intrinsic_height: Optional[int] = Field(default=None, description="Actual intrinsic height if fetched (null by default)")
    srcset: Optional[str] = Field(default=None, description="Raw srcset attribute value")
    loading: Optional[str] = Field(default=None, description="Loading attribute (e.g. lazy, eager)")
    format: Optional[str] = Field(default=None, description="Inferred image extension or mime type")
    caption: Optional[str] = Field(default=None, description="Associated figure caption text")
    nearby_context: Optional[str] = Field(default=None, description="Surrounding DOM text snippet")
    linked_href: Optional[str] = Field(default=None, description="Destination URL if image is wrapped in <a href>")
    is_tracking_or_icon: bool = Field(default=False, description="True if image matches tracking pixel or icon heuristic")
    filter_reason: Optional[str] = Field(default=None, description="Reason if filtered as tracking or icon")
    source_types: List[str] = Field(default_factory=lambda: ["http"], description="Discovery sources ('http', 'browser')")
    provenance: Optional[Provenance] = Field(default=None, description="Traceable source provenance")
    visual_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Placeholder for future vision analysis")

    @model_validator(mode="before")
    @classmethod
    def populate_url_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            u = values.get("url", "")
            if "declared_url" not in values or not values["declared_url"]:
                values["declared_url"] = values.get("resolved_url") or u
            if "resolved_url" not in values or not values["resolved_url"]:
                values["resolved_url"] = u or values["declared_url"]
            if "url" not in values or not values["url"]:
                values["url"] = values["resolved_url"]
            if "width" in values and "declared_width" not in values:
                values["declared_width"] = values["width"]
            if "height" in values and "declared_height" not in values:
                values["declared_height"] = values["height"]
        return values

    # Backward compatibility alias properties
    @property
    def width(self) -> Optional[int]:
        return self.declared_width

    @property
    def height(self) -> Optional[int]:
        return self.declared_height


class LinkEvidence(BaseModel):
    """Observable evidence for an HTML anchor link."""
    href: str = Field(..., description="Target URL")
    source_page: str = Field(..., description="Page URL containing the link")
    anchor_text: str = Field(default="", description="Visible text inside the link tag")
    source_types: List[str] = Field(default_factory=lambda: ["http"], description="Discovery sources")
    is_internal: bool = Field(default=True, description="True if link stays within base domain")
    rel: Optional[str] = Field(default=None, description="rel attribute string")
    target: Optional[str] = Field(default=None, description="target attribute string")
    provenance: Optional[Provenance] = Field(default=None, description="Source location pointer")


class FormInputField(BaseModel):
    """Field definition inside an HTML form."""
    input_type: str = Field(default="text", description="Input type (text, email, submit, etc.)")
    name: Optional[str] = Field(default=None, description="Field name attribute")
    id: Optional[str] = Field(default=None, description="Field id attribute")
    label: Optional[str] = Field(default=None, description="Associated label text")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")


class FormEvidence(BaseModel):
    """Observable evidence for an interactive HTML form."""
    source_page: str = Field(..., description="Page URL containing the form")
    action: Optional[str] = Field(default=None, description="Form action target URL")
    source_types: List[str] = Field(default_factory=lambda: ["http"], description="Discovery sources")
    method: str = Field(default="get", description="HTTP method (get, post)")
    inputs: List[FormInputField] = Field(default_factory=list, description="Form input fields")
    buttons: List[str] = Field(default_factory=list, description="Form submit/action button texts")
    provenance: Optional[Provenance] = Field(default=None, description="Source location pointer")


class DocumentEvidence(BaseModel):
    """Observable evidence for downloadable document resources (PDF, DOCX, ZIP, etc.)."""
    url: str = Field(..., description="Normalized document URL")
    source_page: str = Field(..., description="Page URL referencing the document")
    filename: str = Field(..., description="Base filename")
    file_type: str = Field(..., description="File extension / document type")
    anchor_text: Optional[str] = Field(default=None, description="Link text pointing to document")
    source_types: List[str] = Field(default_factory=lambda: ["http"], description="Discovery sources ('http', 'browser')")
    provenance: Optional[Provenance] = Field(default=None, description="Source location pointer")


class ContactCandidate(BaseModel):
    """Single contact candidate (email, phone, address) extracted from text."""
    value: str = Field(..., description="Extracted raw contact string")
    candidate_type: str = Field(..., description="Candidate type ('email', 'phone', 'address')")
    provenance: Optional[Provenance] = Field(default=None, description="Source pointer")


class ContactEvidence(BaseModel):
    """Observable contact details extracted from DOM text."""
    emails: List[str] = Field(default_factory=list, description="Extracted email strings")
    phone_numbers: List[str] = Field(default_factory=list, description="Extracted phone candidate strings")
    addresses: List[str] = Field(default_factory=list, description="Extracted address candidate strings")
    candidates: List[ContactCandidate] = Field(default_factory=list, description="Typed contact candidate objects")
    provenance_list: List[Provenance] = Field(default_factory=list, description="Source pointers for contact evidence")


class DateCandidate(BaseModel):
    """Single date candidate (visible or machine-readable) extracted from DOM."""
    value: str = Field(..., description="Extracted raw date string")
    candidate_type: str = Field(..., description="Candidate type ('visible_date', 'machine_date')")
    source_types: List[str] = Field(default_factory=lambda: ["http"], description="Discovery sources")
    provenance: Optional[Provenance] = Field(default=None, description="Source pointer")


class DateEvidence(BaseModel):
    """Observable date signals discovered on page."""
    visible_dates: List[str] = Field(default_factory=list, description="Visible date strings observed in text")
    machine_dates: Dict[str, str] = Field(default_factory=dict, description="Metadata or JSON-LD date strings")
    candidates: List[DateCandidate] = Field(default_factory=list, description="Typed date candidate objects")


class PageRoleSignals(BaseModel):
    """Observable signals supporting page role classification."""
    classified_role: str = Field(default="unknown", description="Primary candidate page role (defaults to 'unknown')")
    signals: List[str] = Field(default_factory=list, description="Matched URL, heading, meta, and path signals")


class RenderMetadata(BaseModel):
    """Metadata tracking Playwright browser rendering attempt and outcome."""
    attempted: bool = Field(default=False)
    rendered: bool = Field(default=False)
    render_time_ms: float = Field(default=0.0)
    final_url: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    reasons: List[str] = Field(default_factory=list)
    browser_name: str = Field(default="chromium")
    timeout: Optional[float] = Field(default=None)


class PageEvidence(BaseModel):
    """Structured observable evidence for a single crawled web page."""
    url: str = Field(..., description="Canonical or normalized page URL")
    final_url: Optional[str] = Field(default=None, description="Final URL after HTTP redirects")
    depth: int = Field(default=0, ge=0, description="Discovered crawl depth")
    status: str = Field(default="success", description="Fetch status ('success', 'failed')")
    status_code: int = Field(default=200, description="HTTP response status code")
    content_type: Optional[str] = Field(default="text/html", description="HTTP Content-Type response header")
    discovery_source: str = Field(default="html_link", description="Discovery method")
    
    # Document Identity & Meta
    title: Optional[str] = Field(default=None, description="Page title string")
    meta_description: Optional[str] = Field(default=None, description="Meta description content")
    canonical_url: Optional[str] = Field(default=None, description="Canonical URL link target")
    language: Optional[str] = Field(default=None, description="HTML lang attribute")
    charset: Optional[str] = Field(default=None, description="HTML charset meta declaration")
    
    # Page role signals
    role_signals: PageRoleSignals = Field(default_factory=PageRoleSignals, description="Structured page role signals")
    page_role: str = Field(default="unknown", description="Final page role string")
    
    # Text structure
    word_count: int = Field(default=0, ge=0, description="Clean visible text word count")
    headings: List[Dict[str, str]] = Field(default_factory=list, description="Extracted headings (h1..h6)")
    paragraphs: List[str] = Field(default_factory=list, description="Extracted visible paragraphs")
    lists: List[List[str]] = Field(default_factory=list, description="Extracted list item groups")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted table structures")
    blockquotes: List[str] = Field(default_factory=list, description="Extracted blockquotes")
    captions: List[str] = Field(default_factory=list, description="Extracted figure and table captions")
    
    # Structured collections
    links: List[LinkEvidence] = Field(default_factory=list, description="Discovered HTML links")
    internal_links: List[str] = Field(default_factory=list, description="Internal link target URLs")
    external_links: List[str] = Field(default_factory=list, description="External link target URLs")
    images: List[ImageEvidence] = Field(default_factory=list, description="Discovered image assets")
    forms: List[FormEvidence] = Field(default_factory=list, description="Discovered interactive forms")
    documents: List[DocumentEvidence] = Field(default_factory=list, description="Discovered document resources")
    
    # Metadata & Structured Data
    robots_directives: Dict[str, Any] = Field(default_factory=dict, description="Page-level robots metadata")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted JSON-LD / schema summary")
    jsonld_raw_blocks: List[str] = Field(default_factory=list, description="Raw JSON-LD text payloads")
    meta_tags: List[Dict[str, str]] = Field(default_factory=list, description="All extracted head meta tags")
    
    # Extracted contact & dates
    contacts: ContactEvidence = Field(default_factory=ContactEvidence, description="Extracted contact candidates")
    dates: DateEvidence = Field(default_factory=DateEvidence, description="Extracted date candidates")
    
    # Text extractability metrics
    text_extractability: Dict[str, Any] = Field(default_factory=dict, description="Word boundary collapse & text metrics")
    error: Optional[str] = Field(default=None, description="Error string if page fetch failed")
    # Coexisting Browser Rendering Evidence
    http_evidence: Optional[Dict[str, Any]] = Field(default=None, description="Pre-rendered HTTP evidence snapshot")
    rendered_evidence: Optional[Dict[str, Any]] = Field(default=None, description="Post-rendered browser evidence snapshot")
    render_metadata: Optional[RenderMetadata] = Field(default=None, description="Browser rendering metadata")


    # Excluded internal raw payloads
    html_content: Optional[str] = Field(default=None, exclude=True, description="Internal raw HTML payload")
    headers: Dict[str, str] = Field(default_factory=dict, exclude=True, description="Internal HTTP response headers")


class WebsiteEvidence(BaseModel):
    """Top-level shared site evidence store across all discovery and crawl phases.
    
    Contains pure, objective evidence without AI-readiness scores or findings.
    """
    start_url: str = Field(..., description="Initial target URL")
    normalized_start_url: str = Field(..., description="Normalized starting URL")
    crawl_metadata: Dict[str, Any] = Field(default_factory=dict, description="Crawl configuration, timing, and boundary metadata")
    robots: RobotsEvidence = Field(..., description="Observed robots.txt evidence")
    sitemaps: List[SitemapEvidence] = Field(default_factory=list, description="Observed sitemap evidence items")
    discovered_urls: List[DiscoveredURLEvidence] = Field(default_factory=list, description="All traceable discovered URLs")
    pages: List[PageEvidence] = Field(default_factory=list, description="Store of all crawled page evidence records")
    failed_urls: List[FailedURLEvidence] = Field(default_factory=list, description="Traceable record of failed URLs")
    skipped_urls: List[Dict[str, Any]] = Field(default_factory=list, description="Skipped URL records")
    resource_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary counts of discovered resources")
    
    # Overview counts
    pages_discovered: int = Field(default=0, ge=0, description="Total unique URLs discovered")
    pages_crawled: int = Field(default=0, ge=0, description="Total pages crawled")
    pages_rendered: int = Field(default=0, ge=0, description="Total pages rendered by browser")
    max_depth: int = Field(default=3, ge=0, description="Configured max depth")
    truncated: bool = Field(default=False, description="True if crawl stopped before completing queue")
    truncation_reason: Optional[str] = Field(default=None, description="Reason for crawl truncation")

    @model_validator(mode="before")
    @classmethod
    def map_website_legacy_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "crawled_pages" in values and ("pages" not in values or not values["pages"]):
                values["pages"] = values["crawled_pages"]
        return values

    @property
    def crawled_pages(self) -> List[PageEvidence]:
        """Backward-compatible property for pages list."""
        return self.pages
