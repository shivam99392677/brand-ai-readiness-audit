"""Crawl & Render Audit Skill Implementation (CR-001 through CR-012)."""

from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from src.models import (
    Evidence,
    Finding,
    FindingSeverity,
    FindingStatus,
)

BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section",
    "article", "header", "footer", "nav", "main", "li", "tr", "td", "br"
}
SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}

FRAMEWORK_PAYLOAD_PATTERNS = [
    r"self\.__next_f",
    r"__NEXT_DATA__",
    r"__webpack_require__",
    r"Next\.Metadata",
    r"chunk[a-zA-Z0-9_-]+\.js",
]


class CrawlRenderHTMLParser(HTMLParser):
    """HTML Parser for extracting visible text, headings, meta tags, links, and semantic sections.
    
    Strictly excludes script, style, SVG, noscript, and React/Next.js framework payloads from visible text.
    """

    def __init__(self):
        super().__init__()
        self.title_text: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.canonical_url: Optional[str] = None
        self.headings: List[Dict[str, str]] = []  # [{"tag": "h1", "text": "..."}]
        self.paragraphs: List[str] = []
        self.anchor_links: List[Dict[str, str]] = []  # [{"href": "...", "text": "..."}]
        self.jsonld_blocks: List[str] = []
        self.sections_found: Set[str] = set()

        self._text_chunks: List[str] = []
        self._tag_stack: List[str] = []

        self._in_title = False
        self._title_buffer: List[str] = []

        self._current_heading_tag: Optional[str] = None
        self._heading_buffer: List[str] = []

        self._in_paragraph = False
        self._paragraph_buffer: List[str] = []

        self._in_jsonld = False
        self._jsonld_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        self._tag_stack.append(tag_lower)

        if tag_lower in ("main", "article", "nav", "header", "footer", "section"):
            self.sections_found.add(tag_lower)
        elif tag_lower == "p":
            self._in_paragraph = True
            self._paragraph_buffer = []
        elif tag_lower == "title":
            self._in_title = True
            self._title_buffer = []
        elif tag_lower == "script":
            if attr_dict.get("type", "").strip().lower() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buffer = []
        elif tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "").strip()
            if (name == "description" or prop == "og:description") and content:
                if not self.meta_description:
                    self.meta_description = content
        elif tag_lower == "link":
            rel = attr_dict.get("rel", "").lower()
            href = attr_dict.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical_url = href
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._current_heading_tag = tag_lower
            self._heading_buffer = []
        elif tag_lower == "a":
            href = attr_dict.get("href", "").strip()
            self.anchor_links.append({"href": href, "text": ""})

        if tag_lower in BLOCK_TAGS and not any(t in SKIP_TAGS for t in self._tag_stack):
            self._text_chunks.append(" ")

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if self._tag_stack and self._tag_stack[-1] == tag_lower:
            self._tag_stack.pop()

        if tag_lower == "title" and self._in_title:
            self.title_text = "".join(self._title_buffer).strip()
            self._in_title = False
        elif tag_lower == "p" and self._in_paragraph:
            p_txt = "".join(self._paragraph_buffer).strip()
            if p_txt:
                self.paragraphs.append(p_txt)
            self._in_paragraph = False
        elif tag_lower == "script" and self._in_jsonld:
            j_txt = "".join(self._jsonld_buffer).strip()
            if j_txt:
                self.jsonld_blocks.append(j_txt)
            self._in_jsonld = False
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6") and self._current_heading_tag == tag_lower:
            h_text = "".join(self._heading_buffer).strip()
            if h_text:
                self.headings.append({"tag": tag_lower, "text": h_text})
            self._current_heading_tag = None

        if tag_lower in BLOCK_TAGS and not any(t in SKIP_TAGS for t in self._tag_stack):
            self._text_chunks.append(" ")

    def handle_data(self, data: str):
        if not data:
            return

        # 1. Skip non-visible tags
        if any(t in SKIP_TAGS for t in self._tag_stack):
            if self._in_jsonld:
                self._jsonld_buffer.append(data)
            return

        # 2. Skip Framework / Next.js payloads
        for pat in FRAMEWORK_PAYLOAD_PATTERNS:
            if re.search(pat, data):
                return

        if self._in_title:
            self._title_buffer.append(data)

        if self._in_paragraph:
            self._paragraph_buffer.append(data)

        if self._current_heading_tag:
            self._heading_buffer.append(data)

        self._text_chunks.append(data)

    def get_extracted_text(self) -> Tuple[str, str]:
        """Returns (raw_text, normalized_text)."""
        raw_text = "".join(self._text_chunks)
        normalized = " ".join(raw_text.split())
        return raw_text, normalized


def detect_word_boundary_collapse(text: str) -> Tuple[bool, List[str]]:
    """Detects suspicious word-boundary collapse where words run together without spaces."""
    if not text:
        return False, []

    tokens = re.findall(r"[A-Za-z]{25,}", text)
    suspicious = []
    for tok in tokens:
        tok_lower = tok.lower()
        if not (tok_lower.startswith("http") or tok_lower.startswith("data:") or "stylesheet" in tok_lower):
            suspicious.append(tok)

    words = text.split()
    avg_word_len = (sum(len(w) for w in words) / len(words)) if words else 0
    is_collapsed = len(suspicious) > 0 or (len(text) > 100 and avg_word_len > 20)

    return is_collapsed, suspicious[:5]


def audit_crawl_render_skill(
    url: str,
    html_content: str = "",
    headers: Optional[Dict[str, str]] = None,
    status_code: int = 200,
    rendered_html_content: Optional[str] = None,
    crawl_manifest: Optional[Any] = None,
) -> List[Finding]:
    """Executes crawl & render accessibility, extractability, and discoverability checks (CR-001 through CR-012)."""
    headers = headers or {}
    findings: List[Finding] = []

    parser = CrawlRenderHTMLParser()
    parser.feed(html_content)
    raw_text, normalized_text = parser.get_extracted_text()

    # CR-001: HTTP Response Status
    if status_code == 200:
        ev1 = Evidence(
            source_url=url,
            evidence_type="http_status",
            observed={"status_code": status_code, "reason": "OK"},
            location="HTTP Response Line",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-001",
            title="HTTP Response Status",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="Target URL responded with HTTP 200 OK status.",
            evidence=[ev1],
            recommendation="Maintain page availability and 200 OK HTTP response codes.",
        ))
    else:
        ev1 = Evidence(
            source_url=url,
            evidence_type="http_status",
            observed={"status_code": status_code},
            expected={"status_code": 200},
            location="HTTP Response Line",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-001",
            title="HTTP Response Status",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description=f"Target URL responded with non-200 HTTP status code: {status_code}.",
            evidence=[ev1],
            recommendation="Ensure target URL returns a 200 OK status code to allow crawler indexing.",
        ))

    # CR-002: AI Crawler Robots Directives
    x_robots_tag = headers.get("x-robots-tag", "").lower()
    if "noindex" in x_robots_tag:
        ev2 = Evidence(
            source_url=url,
            evidence_type="http_header",
            observed={"x-robots-tag": headers.get("x-robots-tag")},
            expected={"x-robots-tag": "index, follow or omitted"},
            location="HTTP Header: X-Robots-Tag",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-002",
            title="AI Crawler Robots Directives",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description="HTTP header X-Robots-Tag contains 'noindex', restricting crawler indexing.",
            evidence=[ev2],
            recommendation="Remove restrictive noindex directives from X-Robots-Tag header.",
        ))
    else:
        ev2 = Evidence(
            source_url=url,
            evidence_type="http_header",
            observed={"x-robots-tag": headers.get("x-robots-tag", "[None]")},
            location="HTTP Header: X-Robots-Tag",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-002",
            title="AI Crawler Robots Directives",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="No restrictive noindex directives were detected in HTTP headers.",
            evidence=[ev2],
            recommendation="Ensure robots directives permit public indexing.",
        ))

    # CR-003: Pre-Rendering Content Availability
    stripped_html = html_content.strip()
    if len(stripped_html) < 200 and ("root" in stripped_html or "app" in stripped_html):
        ev3 = Evidence(
            source_url=url,
            evidence_type="dom_prerender",
            observed={"html_length": len(stripped_html), "snippet": stripped_html[:100]},
            expected={"html_length": ">= 200 bytes static text"},
            location="HTML Body",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-003",
            title="Pre-Rendering Content Availability",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description="Pre-rendered HTML payload contains minimal static text, indicating heavy reliance on client-side JS rendering.",
            evidence=[ev3],
            recommendation="Implement Server-Side Rendering (SSR) or static pre-rendering for core page content.",
        ))
    else:
        ev3 = Evidence(
            source_url=url,
            evidence_type="dom_prerender",
            observed={"html_length": len(stripped_html)},
            location="HTML Body",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-003",
            title="Pre-Rendering Content Availability",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="Pre-rendered HTML contains static content accessible without client-side JS execution.",
            evidence=[ev3],
            recommendation="Maintain server-side content availability.",
        ))

    # CR-004: Text Extractability & Word Boundary Integrity
    is_collapsed, suspicious_tokens = detect_word_boundary_collapse(normalized_text)
    if is_collapsed:
        ev4 = Evidence(
            source_url=url,
            evidence_type="text_extractability",
            observed={
                "raw_text_length": len(raw_text),
                "normalized_text_length": len(normalized_text),
                "word_boundary_collapse_detected": True,
                "suspicious_tokens": suspicious_tokens,
            },
            expected={"word_boundary_collapse_detected": False},
            location="DOM Text Nodes",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-004",
            title="Text Extractability & Word Boundary Integrity",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description=f"Detected suspicious word-boundary collapse in extracted text (e.g. '{suspicious_tokens[0] if suspicious_tokens else ''}'). Words run together without space delimiters in DOM extraction.",
            evidence=[ev4],
            recommendation="Ensure spaces or block elements separate words in HTML markup instead of relying purely on visual CSS spacing.",
        ))
    else:
        ev4 = Evidence(
            source_url=url,
            evidence_type="text_extractability",
            observed={
                "raw_text_length": len(raw_text),
                "normalized_text_length": len(normalized_text),
                "word_boundary_collapse_detected": False,
            },
            location="DOM Text Nodes",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-004",
            title="Text Extractability & Word Boundary Integrity",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="Extracted text preserves word boundaries and whitespace formatting.",
            evidence=[ev4],
            recommendation="Maintain clean DOM text node formatting.",
        ))

    # CR-005: Page Title
    title_val = parser.title_text
    title_len = len(title_val) if title_val else 0
    if not title_val or title_len == 0:
        ev5 = Evidence(
            source_url=url,
            evidence_type="page_title",
            observed={"title": None, "length": 0},
            expected={"title": "Non-empty descriptive title string"},
            location="<head> > <title>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-005",
            title="Page Title Presence & Quality",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description="Page is missing a <title> tag.",
            evidence=[ev5],
            recommendation="Add a descriptive <title> tag to the HTML head.",
        ))
    elif title_len < 5:
        ev5 = Evidence(
            source_url=url,
            evidence_type="page_title",
            observed={"title": title_val, "length": title_len},
            expected={"title_length": ">= 5 characters"},
            location="<head> > <title>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-005",
            title="Page Title Presence & Quality",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description=f"Page title '{title_val}' is unusually short ({title_len} characters).",
            evidence=[ev5],
            recommendation="Provide a more descriptive page title.",
        ))
    else:
        ev5 = Evidence(
            source_url=url,
            evidence_type="page_title",
            observed={"title": title_val, "length": title_len},
            location="<head> > <title>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-005",
            title="Page Title Presence & Quality",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Descriptive page title detected: '{title_val}' ({title_len} characters).",
            evidence=[ev5],
            recommendation="Maintain accurate page title tags.",
        ))

    # CR-006: Meta Description
    meta_desc = parser.meta_description
    desc_len = len(meta_desc) if meta_desc else 0
    if not meta_desc:
        ev6 = Evidence(
            source_url=url,
            evidence_type="meta_description",
            observed={"description": None, "length": 0},
            expected={"description": "Non-empty meta description tag"},
            location="<head> > <meta name='description'>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-006",
            title="Meta Description Presence",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description="Page is missing a meta description tag.",
            evidence=[ev6],
            recommendation="Add a concise meta description summarizing the page content.",
        ))
    else:
        ev6 = Evidence(
            source_url=url,
            evidence_type="meta_description",
            observed={"description": meta_desc, "length": desc_len},
            location="<head> > <meta name='description'>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-006",
            title="Meta Description Presence",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Meta description present ({desc_len} characters): '{meta_desc[:60]}...'",
            evidence=[ev6],
            recommendation="Maintain concise meta descriptions.",
        ))

    # CR-007: Heading Structure
    h1_list = [h for h in parser.headings if h["tag"] == "h1"]
    h1_count = len(h1_list)
    h1_texts = [h["text"] for h in h1_list]

    malformed_h1s = []
    for txt in h1_texts:
        collapsed, _ = detect_word_boundary_collapse(txt)
        if collapsed:
            malformed_h1s.append(txt)

    if h1_count == 0:
        ev7 = Evidence(
            source_url=url,
            evidence_type="heading_structure",
            observed={"h1_count": 0, "h1_texts": [], "total_headings": len(parser.headings)},
            expected={"h1_count": ">= 1"},
            location="<body> heading elements",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-007",
            title="Heading Structure & H1 Quality",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description="No <h1> heading element was found on the page.",
            evidence=[ev7],
            recommendation="Include a primary <h1> heading summarizing the main page topic.",
        ))
    elif malformed_h1s:
        ev7 = Evidence(
            source_url=url,
            evidence_type="heading_structure",
            observed={"h1_count": h1_count, "h1_texts": h1_texts, "malformed_h1s": malformed_h1s},
            expected={"h1_text_formatting": "Clean spaces between heading words"},
            location="<h1> tag",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-007",
            title="Heading Structure & H1 Quality",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description=f"Extracted <h1> heading exhibits word-boundary collapse: '{malformed_h1s[0]}'. Words run together without space delimiters.",
            evidence=[ev7],
            recommendation="Ensure spaces are preserved inside <h1> tags.",
        ))
    else:
        ev7 = Evidence(
            source_url=url,
            evidence_type="heading_structure",
            observed={"h1_count": h1_count, "h1_texts": h1_texts, "total_headings": len(parser.headings)},
            location="<h1> tag",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-007",
            title="Heading Structure & H1 Quality",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Found {h1_count} <h1> heading(s): '{h1_texts[0]}'.",
            evidence=[ev7],
            recommendation="Maintain logical heading hierarchy.",
        ))

    # CR-008: Internal Links
    parsed_base = urlparse(url)
    target_netloc = parsed_base.netloc.lower()

    internal_links: List[str] = []
    external_links: List[str] = []
    js_nav_links: List[str] = []

    for a in parser.anchor_links:
        href = a["href"]
        if not href or href.startswith("javascript:") or href == "#":
            js_nav_links.append(href)
            continue
        p = urlparse(href)
        if not p.netloc or p.netloc.lower() == target_netloc:
            internal_links.append(href)
        else:
            external_links.append(href)

    if internal_links:
        ev8 = Evidence(
            source_url=url,
            evidence_type="internal_links",
            observed={
                "internal_link_count": len(internal_links),
                "external_link_count": len(external_links),
                "js_nav_link_count": len(js_nav_links),
                "sample_internal_urls": internal_links[:5],
            },
            location="<a href> tags",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-008",
            title="Discoverable Internal Links",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Discovered {len(internal_links)} internal link(s) for automated crawling.",
            evidence=[ev8],
            recommendation="Ensure core navigation links are discoverable via standard <a href> tags.",
        ))
    else:
        ev8 = Evidence(
            source_url=url,
            evidence_type="internal_links",
            observed={
                "internal_link_count": 0,
                "external_link_count": len(external_links),
                "js_nav_link_count": len(js_nav_links),
            },
            expected={"internal_link_count": ">= 1"},
            location="<a href> tags",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-008",
            title="Discoverable Internal Links",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description="No discoverable internal links were found in the HTML anchors.",
            evidence=[ev8],
            recommendation="Expose internal site pages via standard HTML anchor links.",
        ))

    # CR-009: Canonical URL
    canonical_val = parser.canonical_url
    if canonical_val:
        is_match = (canonical_val.strip().rstrip("/") == url.strip().rstrip("/"))
        ev9 = Evidence(
            source_url=url,
            evidence_type="canonical_url",
            observed={"canonical_url": canonical_val, "target_url": url, "is_match": is_match},
            location="<head> > <link rel='canonical'>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-009",
            title="Canonical URL Declaration",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Canonical URL declared: '{canonical_val}'.",
            evidence=[ev9],
            recommendation="Ensure canonical URLs point to target domain canonical endpoints.",
        ))
    else:
        ev9 = Evidence(
            source_url=url,
            evidence_type="canonical_url",
            observed={"canonical_url": None, "target_url": url},
            expected={"canonical_url": url},
            location="<head> > <link rel='canonical'>",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-009",
            title="Canonical URL Declaration",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description="No canonical URL link tag (<link rel='canonical'>) was declared.",
            evidence=[ev9],
            recommendation="Add a self-referential canonical URL tag.",
        ))

    # CR-010: Site-Wide Content Discoverability
    if crawl_manifest is not None and hasattr(crawl_manifest, "pages") and len(crawl_manifest.pages) > 0:
        pages = crawl_manifest.pages
        total_site_words = sum(getattr(p, "word_count", 0) for p in pages)
        pages_crawled_count = len(pages)
        roles_dict: Dict[str, int] = {}
        for p in pages:
            r = getattr(p, "page_role", "other")
            roles_dict[r] = roles_dict.get(r, 0) + 1

        homepage_p = next((p for p in pages if getattr(p, "page_role", "") == "homepage"), None)
        homepage_words = getattr(homepage_p, "word_count", 0) if homepage_p else len(normalized_text.split())

        content_bearing_count = sum(1 for p in pages if getattr(p, "word_count", 0) >= 100)

        obs_text = (
            f"OBSERVATION: Homepage contains {homepage_words} words. "
            f"Across {pages_crawled_count} site-wide page(s), extracted {total_site_words} total words "
            f"covering page roles: {dict(sorted(roles_dict.items()))}. ({content_bearing_count} pages contain >100 words)."
        )
        interp_text = "INTERPRETATION: Site-wide brand information is discoverable across multiple reachable internal pages."
        impact_text = "IMPACT: AI agents traversing discoverable internal links will extract complete product and company context."
        rec_text = "RECOMMENDATION: Maintain clear internal links and semantic headings across role pages."

        ev10 = Evidence(
            source_url=url,
            evidence_type="sitewide_content_discoverability",
            observed={
                "homepage_word_count": homepage_words,
                "total_site_words": total_site_words,
                "pages_crawled_count": pages_crawled_count,
                "content_bearing_pages_count": content_bearing_count,
                "page_roles_breakdown": roles_dict,
                "observation": obs_text,
                "interpretation": interp_text,
                "impact": impact_text,
            },
            location="Site-Wide Crawl Manifest Store",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-010",
            title="Site-Wide Content Discoverability",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"{obs_text} {interp_text}",
            evidence=[ev10],
            recommendation=rec_text,
        ))
    else:
        word_count = len(normalized_text.split())
        sections_list = sorted(list(parser.sections_found))

        if word_count >= 50 or sections_list or len(parser.paragraphs) > 0:
            obs_text = f"OBSERVATION: Page contains {word_count} extracted words and {len(parser.paragraphs)} paragraphs across sections {sections_list}."
            interp_text = "INTERPRETATION: Static page content is discoverable for machine extraction."
            impact_text = "IMPACT: AI systems can parse initial page information directly."
            rec_text = "RECOMMENDATION: Maintain semantic HTML tags (<main>, <article>, <section>) to assist automated content extraction."

            ev10 = Evidence(
                source_url=url,
                evidence_type="content_discoverability",
                observed={
                    "word_count": word_count,
                    "paragraph_count": len(parser.paragraphs),
                    "sections_found": sections_list,
                    "observation": obs_text,
                    "interpretation": interp_text,
                    "impact": impact_text,
                },
                location="HTML Body Structure",
            )
            findings.append(Finding(
                skill="crawl-render-audit",
                check_id="CR-010",
                title="Content Discoverability & Structural Sections",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"{obs_text} {interp_text}",
                evidence=[ev10],
                recommendation=rec_text,
            ))
        else:
            obs_text = f"OBSERVATION: Page contains minimal visible text ({word_count} words extracted)."
            interp_text = "INTERPRETATION: Key site content may be sparse or locked behind client-side rendering."
            impact_text = "IMPACT: AI engines relying on static parsing may extract incomplete brand data."
            rec_text = "RECOMMENDATION: Expose core narrative and content sections directly in static HTML markup."

            ev10 = Evidence(
                source_url=url,
                evidence_type="content_discoverability",
                observed={
                    "word_count": word_count,
                    "paragraph_count": len(parser.paragraphs),
                    "sections_found": sections_list,
                    "observation": obs_text,
                    "interpretation": interp_text,
                    "impact": impact_text,
                },
                expected={"word_count": ">= 50 words"},
                location="HTML Body Structure",
            )
            findings.append(Finding(
                skill="crawl-render-audit",
                check_id="CR-010",
                title="Content Discoverability & Structural Sections",
                status=FindingStatus.WARNING,
                severity=FindingSeverity.MEDIUM,
                description=f"{obs_text} {interp_text}",
                evidence=[ev10],
                recommendation=rec_text,
            ))

    # CR-011: Raw HTML vs Rendered HTML
    if rendered_html_content is not None:
        r_parser = CrawlRenderHTMLParser()
        r_parser.feed(rendered_html_content)
        _, r_normalized = r_parser.get_extracted_text()

        raw_len = len(normalized_text)
        rendered_len = len(r_normalized)
        diff = rendered_len - raw_len

        ev11 = Evidence(
            source_url=url,
            evidence_type="raw_vs_rendered_text",
            observed={
                "raw_text_length": raw_len,
                "rendered_text_length": rendered_len,
                "difference": diff,
            },
            location="Raw HTML vs Rendered DOM",
        )
        if raw_len < (rendered_len * 0.5):
            findings.append(Finding(
                skill="crawl-render-audit",
                check_id="CR-011",
                title="Raw vs Rendered Text Discrepancy",
                status=FindingStatus.WARNING,
                severity=FindingSeverity.MEDIUM,
                description=f"Significant text content added during JS rendering (raw: {raw_len} chars vs rendered: {rendered_len} chars). Non-JS crawlers will miss content.",
                evidence=[ev11],
                recommendation="Use Server-Side Rendering (SSR) to make JS-rendered content accessible to static crawlers.",
            ))
        else:
            findings.append(Finding(
                skill="crawl-render-audit",
                check_id="CR-011",
                title="Raw vs Rendered Text Discrepancy",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description=f"Raw HTML contains substantially all content present in rendered DOM (raw: {raw_len} vs rendered: {rendered_len} chars).",
                evidence=[ev11],
                recommendation="Maintain SSR parity.",
            ))
    else:
        ev11 = Evidence(
            source_url=url,
            evidence_type="raw_vs_rendered_text",
            observed={"browser_rendering_available": False},
            location="Headless Browser Engine",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-011",
            title="Raw vs Rendered Text Discrepancy",
            status=FindingStatus.NOT_APPLICABLE,
            severity=FindingSeverity.INFO,
            description="Headless browser rendering comparison was not active during this audit pass.",
            evidence=[ev11],
            recommendation="N/A",
        ))

    # CR-012: Site Crawl Coverage
    if crawl_manifest is not None:
        p_discovered = getattr(crawl_manifest, "pages_discovered", 1)
        p_crawled = getattr(crawl_manifest, "pages_crawled", 1)
        m_depth = getattr(crawl_manifest, "max_depth", 3)
        is_truncated = getattr(crawl_manifest, "truncated", False)
        t_reason = getattr(crawl_manifest, "truncation_reason", None)

        roles_count: Dict[str, int] = {}
        pages_list = getattr(crawl_manifest, "pages", [])
        for p in pages_list:
            r = getattr(p, "page_role", "other")
            roles_count[r] = roles_count.get(r, 0) + 1

        ev12 = Evidence(
            source_url=url,
            evidence_type="site_crawl_coverage",
            observed={
                "pages_discovered": p_discovered,
                "pages_crawled": p_crawled,
                "max_depth": m_depth,
                "truncated": is_truncated,
                "truncation_reason": t_reason,
                "page_roles": dict(sorted(roles_count.items())),
            },
            location="Site Crawler Manifest Engine",
        )

        status_cr12 = FindingStatus.WARNING if is_truncated else FindingStatus.PASS
        severity_cr12 = FindingSeverity.LOW if is_truncated else FindingSeverity.INFO

        desc_cr12 = f"Crawled {p_crawled} of {p_discovered} discovered pages up to depth {m_depth} across page roles: {dict(sorted(roles_count.items()))}."
        if is_truncated and t_reason:
            desc_cr12 += f" Crawl was bounded by limit: {t_reason}."

        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-012",
            title="Site Crawl Coverage",
            status=status_cr12,
            severity=severity_cr12,
            description=desc_cr12,
            evidence=[ev12],
            recommendation="Maintain crawlable internal link structures across primary brand pages.",
        ))
    else:
        ev12 = Evidence(
            source_url=url,
            evidence_type="site_crawl_coverage",
            observed={
                "internal_link_count": len(internal_links),
                "sample_targets": internal_links[:5],
            },
            location="Homepage <a href> links",
        )
        findings.append(Finding(
            skill="crawl-render-audit",
            check_id="CR-012",
            title="Site Crawl Coverage",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description=f"Homepage exposes {len(internal_links)} internal link target(s) for site-wide crawling.",
            evidence=[ev12],
            recommendation="Ensure internal target URLs remain crawlable.",
        ))

    return findings


def run_crawl_render_audit(
    evidence: Any,
    website: Optional[Any] = None,
    url: Optional[str] = None,
    html_content: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    status_code: Optional[int] = None,
    crawl_manifest: Optional[Any] = None,
    **kwargs,
) -> List[Finding]:
    """Canonical entrypoint for crawl and render accessibility audit skill."""
    target_url = url or (getattr(website, "start_url", None) if website else None) or "https://example.com"
    
    # 1. Direct parameter fallback
    if html_content is not None or headers is not None:
        return audit_crawl_render_skill(
            url=target_url,
            html_content=html_content or "",
            headers=headers or {},
            status_code=status_code or 200,
            crawl_manifest=crawl_manifest,
        )

    # 2. Extract homepage or primary page from WebsiteEvidence
    p_html = ""
    p_headers = {}
    p_status = 200
    if website is not None and hasattr(website, "pages") and website.pages:
        primary_page = next((p for p in website.pages if getattr(p, "url", "") == target_url or getattr(p, "depth", 0) == 0), website.pages[0])
        p_html = getattr(primary_page, "html_content", "") or ""
        p_headers = getattr(primary_page, "headers", {}) or {}
        p_status = getattr(primary_page, "status_code", 200) or 200
    elif hasattr(evidence, "evidence"):
        raw_ev = next((e for e in evidence.evidence if e.type == "raw_html"), None)
        if raw_ev:
            p_html = raw_ev.data.get("html_content", "")

    return audit_crawl_render_skill(
        url=target_url,
        html_content=p_html,
        headers=p_headers,
        status_code=p_status,
        crawl_manifest=crawl_manifest,
    )

