
from pathlib import Path

engine_code = """\"\"\"Core Site Crawler Engine implementing objective URL discovery, bounded crawling, hybrid HTTP + selective Playwright browser rendering, and WebsiteEvidence store.\"\"\"

import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import requests
from pydantic import BaseModel, Field

from src.analysis.crawl_render_audit import detect_word_boundary_collapse
from src.crawler.browser import BrowserRenderer, RenderedPageResult
from src.crawler.prioritizer import calculate_url_priority, sort_urls_by_priority
from src.crawler.render_decision import RenderDecision, should_render_page
from src.crawler.robots import RobotsChecker
from src.crawler.role_classifier import classify_page_role_signals
from src.crawler.sitemap import SitemapDiscoverer
from src.crawler.url_utils import extract_base_domain, is_crawlable_html_url, normalize_url
from src.evidence.models import (
    DiscoveredURLEvidence,
    DocumentEvidence,
    FailedURLEvidence,
    FormEvidence,
    ImageEvidence,
    LinkEvidence,
    PageEvidence,
    Provenance,
    RenderMetadata,
    RobotsEvidence,
    SitemapEvidence,
    WebsiteEvidence,
)
from src.extraction.images import extract_page_images
from src.extraction.links import extract_page_links_and_resources
from src.extraction.metadata import extract_page_metadata
from src.extraction.page import extract_page_content
from src.extraction.structured_data import extract_structured_data


class CrawlConfig(BaseModel):
    \"\"\"Configuration for site-wide crawling and discovery bounds.\"\"\"
    max_depth: int = Field(default=3, ge=0, description="Maximum crawl depth from starting URL")
    max_pages: int = Field(default=100, ge=1, description="Maximum total pages to crawl")
    same_domain_only: bool = Field(default=True, description="Restrict crawling to starting domain")
    respect_robots: bool = Field(default=True, description="Enforce robots.txt fetch permissions")
    request_timeout_seconds: float = Field(default=3.0, ge=1.0, description="HTTP request timeout")
    max_requests_per_second: float = Field(default=2.0, ge=0.1, description="Request rate limit governor")
    discover_sitemap: bool = Field(default=True, description="Discover and parse sitemap.xml")
    user_agent: str = Field(default="AIReadinessAudit/0.1.0", description="User-Agent string for HTTP requests")
    
    # Browser rendering configuration
    browser_enabled: bool = Field(default=True, description="Enable selective Playwright browser rendering")
    browser_type: str = Field(default="chromium", description="Browser type")
    browser_page_timeout_seconds: float = Field(default=15.0, ge=1.0, description="Browser page navigation timeout")
    max_rendered_pages: int = Field(default=10, ge=0, description="Maximum pages to render via browser per crawl")


class CrawlManifest(BaseModel):
    \"\"\"Backward-compatible wrapper for WebsiteEvidence store.\"\"\"
    start_url: str = Field(..., description="Initial starting URL of the audit")
    pages_discovered: int = Field(..., ge=0, description="Total unique URLs discovered during crawl")
    pages_crawled: int = Field(..., ge=0, description="Total pages successfully or attempt-crawled")
    max_depth: int = Field(..., ge=0, description="Configured maximum crawl depth")
    truncated: bool = Field(..., description="True if crawl stopped before discovering all inventory URLs")
    truncation_reason: Optional[str] = Field(default=None, description="Reason for crawl truncation")
    robots_status: Dict[str, Any] = Field(default_factory=dict, description="Robots.txt check metadata")
    sitemap_status: Dict[str, Any] = Field(default_factory=dict, description="Sitemap.xml discovery metadata")
    failed_urls: List[Dict[str, Any]] = Field(default_factory=list, description="Failed URL records")
    skipped_urls: List[Dict[str, Any]] = Field(default_factory=list, description="Skipped URL records")
    pages: List[PageEvidence] = Field(default_factory=list, description="All crawled page evidence records")
    website_evidence: Optional[WebsiteEvidence] = Field(default=None, description="Full WebsiteEvidence store")


class SiteCrawler:
    \"\"\"Site-wide Crawler Engine supporting HTTP-first fetching with selective Playwright rendering.\"\"\"

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig()
        self.robots_checker = RobotsChecker(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        self.sitemap_discoverer = SitemapDiscoverer(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.request_timeout_seconds,
        )
        self.browser_renderer = BrowserRenderer(
            browser_type=self.config.browser_type,
            timeout_seconds=self.config.browser_page_timeout_seconds,
        )

    def crawl_site(
        self,
        start_url: str,
        html_override: Optional[str] = None,
        custom_fetcher: Optional[Callable[[str], tuple]] = None,
    ) -> CrawlManifest:
        \"\"\"Executes bounded, priority-driven site crawl with HTTP-first strategy and selective browser rendering.\"\"\"
        start_time = time.time()
        norm_start = normalize_url(start_url)
        if not norm_start:
            raise ValueError(f"Invalid starting URL for site crawler: {start_url}")

        base_domain = extract_base_domain(norm_start)

        # 1. ROBOTS.TXT CHECK
        robots_evidence = self.robots_checker.fetch_and_parse(norm_start)
        robots_info = {
            "available": robots_evidence.available,
            "status_code": robots_evidence.status_code,
            "url": robots_evidence.url,
            "sitemaps_declared": robots_evidence.sitemaps_declared,
        }

        # 2. SITEMAP.XML DISCOVERY
        sitemap_urls_to_check = list(robots_evidence.sitemaps_declared)
        default_sitemap = f"https://{base_domain}/sitemap.xml"
        if default_sitemap not in sitemap_urls_to_check:
            sitemap_urls_to_check.append(default_sitemap)

        sitemap_evidence_items: List[SitemapEvidence] = []
        sitemap_discovered_urls: Set[str] = set()

        if self.config.discover_sitemap:
            for sm_url in sitemap_urls_to_check[:3]:
                sm_ev = self.sitemap_discoverer.fetch_and_parse(sm_url)
                sitemap_evidence_items.append(sm_ev)
                for u in sm_ev.urls_discovered:
                    sitemap_discovered_urls.add(u)

        sitemap_info = {
            "discovered": len(sitemap_evidence_items) > 0 and any(s.available for s in sitemap_evidence_items),
            "sitemaps_parsed": len(sitemap_evidence_items),
            "urls_from_sitemap": len(sitemap_discovered_urls),
        }

        # 3. URL QUEUE & TRACKING STRUCTURES
        discovered_urls: Dict[str, DiscoveredURLEvidence] = {}
        crawled_pages: List[PageEvidence] = []
        failed_url_records: List[FailedURLEvidence] = []
        failed_urls_compat: List[Dict[str, Any]] = []
        skipped_urls: List[Dict[str, Any]] = []
        visited_urls: Set[str] = set()
        pages_rendered_count = 0

        def add_to_inventory(
            raw_url: str,
            depth: int,
            parent_url: Optional[str] = None,
            anchor: Optional[str] = None,
            discovery_method: str = "html_link",
        ) -> bool:
            n_url = normalize_url(raw_url, base_url=parent_url or norm_start)
            if not n_url:
                return False

            if self.config.same_domain_only and extract_base_domain(n_url) != base_domain:
                return False

            if not is_crawlable_html_url(n_url):
                return False

            if n_url not in discovered_urls:
                prio = calculate_url_priority(
                    url=n_url,
                    depth=depth,
                    discovery_source=discovery_method,
                    anchor_text=anchor,
                )
                prov = Provenance(
                    source_url=parent_url or norm_start,
                    location="a.href" if discovery_method == "html_link" else discovery_method,
                    discovery_method=discovery_method,
                )
                disc_ev = DiscoveredURLEvidence(
                    url=n_url,
                    discovered_from=parent_url,
                    discovery_method=discovery_method,
                    depth=depth,
                    anchor_text=anchor,
                    priority=prio,
                    provenance=prov,
                )
                discovered_urls[n_url] = disc_ev
                return True
            return False

        # Add start URL to inventory
        add_to_inventory(norm_start, depth=0, parent_url=None, anchor="Start URL", discovery_method="start_url")

        # Add sitemap URLs to inventory at depth 1
        for sm_u in sorted(list(sitemap_discovered_urls)):
            add_to_inventory(sm_u, depth=1, parent_url=norm_start, anchor="Sitemap URL", discovery_method="sitemap")

        # 4. BOUNDED CRAWL LOOP
        while len(crawled_pages) < self.config.max_pages:
            unvisited = [u for u in discovered_urls.keys() if u not in visited_urls]
            if not unvisited:
                break

            sorted_unvisited = sort_urls_by_priority(unvisited, discovered_urls)
            curr_url = sorted_unvisited[0]
            visited_urls.add(curr_url)

            disc_meta = discovered_urls[curr_url]
            curr_depth = disc_meta.depth
            parent_url = disc_meta.discovered_from
            curr_anchor = disc_meta.anchor_text
            disc_method = disc_meta.discovery_method

            if curr_depth > self.config.max_depth:
                skipped_urls.append({"url": curr_url, "reason": f"depth_exceeds_max ({curr_depth} > {self.config.max_depth})"})
                continue

            if self.config.respect_robots and not self.robots_checker.is_allowed(curr_url, robots_evidence):
                skipped_urls.append({"url": curr_url, "reason": "blocked_by_robots_txt"})
                continue

            # Execute HTTP Fetch (PRIMARY PATH)
            html = ""
            status_code = 200
            headers: Dict[str, str] = {}
            final_url = curr_url
            fetch_error = None

            if html_override and curr_url == norm_start:
                html = html_override
                status_code = 200
            elif custom_fetcher:
                try:
                    res_tuple = custom_fetcher(curr_url)
                    if len(res_tuple) == 3:
                        html, headers, status_code = res_tuple
                    elif len(res_tuple) == 2:
                        html, status_code = res_tuple
                        headers = {}
                    final_url = curr_url
                except Exception as cf_err:
                    fetch_error = str(cf_err)
                    status_code = 0
            else:
                try:
                    resp = requests.get(
                        curr_url,
                        headers={"User-Agent": self.config.user_agent},
                        timeout=self.config.request_timeout_seconds,
                        allow_redirects=True,
                    )
                    status_code = resp.status_code
                    headers = dict(resp.headers)
                    html = resp.text
                    final_url = resp.url
                except Exception as net_err:
                    fetch_error = str(net_err)
                    status_code = 0

            if fetch_error or status_code not in (200, 301, 302):
                err_msg = fetch_error or f"HTTP {status_code}"
                failed_ev = FailedURLEvidence(
                    url=curr_url,
                    status_code=status_code,
                    error_reason=err_msg,
                    discovered_from=parent_url,
                    anchor_text=curr_anchor,
                    discovery_method=disc_method,
                    provenance=Provenance(source_url=curr_url, location="http_fetch"),
                )
                failed_url_records.append(failed_ev)
                failed_urls_compat.append({"url": curr_url, "status_code": status_code, "error": err_msg})
                
                crawled_pages.append(PageEvidence(
                    url=curr_url,
                    final_url=final_url,
                    depth=curr_depth,
                    status="failed",
                    status_code=status_code,
                    discovery_source=disc_method,
                    page_role="unknown",
                    error=err_msg,
                ))
                continue

            # 5. EXTRACT HTTP EVIDENCE
            http_meta = extract_page_metadata(html_content=html, url=curr_url)
            http_content = extract_page_content(html_content=html, url=curr_url)
            http_images = extract_page_images(html_content=html, url=curr_url)
            http_resources = extract_page_links_and_resources(html_content=html, url=curr_url)
            http_sd = extract_structured_data(html_content=html, url=curr_url)

            http_evidence_dict = {
                "title": http_meta["title"],
                "meta_description": http_meta["meta_description"],
                "word_count": http_content["word_count"],
                "headings": http_content["headings"],
                "paragraphs": http_content["paragraphs"],
                "links": [l.model_dump() for l in http_resources["links"]],
                "images": [i.model_dump() for i in http_images],
                "structured_data": http_sd["summary"],
            }

            for link_ev in http_resources["links"]:
                link_ev.source_types = ["http"]
            for img_ev in http_images:
                img_ev.source_types = ["http"]
            for form_ev in http_resources["forms"]:
                form_ev.source_types = ["http"]
            for doc_ev in http_resources["documents"]:
                doc_ev.source_types = ["http"]

            # 6. RENDER DECISION (DETERMINISTIC & EXPLAINABLE)
            render_decision = should_render_page(
                url=curr_url,
                html=html,
                headers=headers,
                word_count=http_content["word_count"],
                raw_text_len=len(http_content["raw_text"]),
                links_count=len(http_resources["links"]),
            )

            rendered_evidence_dict = None
            render_meta = RenderMetadata(
                attempted=False,
                rendered=False,
                reasons=render_decision.reasons,
                browser_name=self.config.browser_type,
                timeout=self.config.browser_page_timeout_seconds,
            )

            final_links = list(http_resources["links"])
            final_images = list(http_images)
            final_forms = list(http_resources["forms"])
            final_documents = list(http_resources["documents"])
            final_title = http_meta["title"]
            final_meta_desc = http_meta["meta_description"]
            final_word_count = http_content["word_count"]
            final_headings = http_content["headings"]
            final_paragraphs = http_content["paragraphs"]
            final_lists = http_content["lists"]
            final_tables = http_content["tables"]
            final_blockquotes = http_content["blockquotes"]
            final_contacts = http_content["contacts"]
            final_dates = http_content["dates"]
            final_sd = http_sd

            # 7. SELECTIVE BROWSER RENDERING (IF REQUIRED)
            if (
                self.config.browser_enabled
                and render_decision.required
                and pages_rendered_count < self.config.max_rendered_pages
            ):
                render_result = self.browser_renderer.render(curr_url)
                pages_rendered_count += 1

                if render_result.rendered and render_result.html:
                    r_html = render_result.html
                    r_meta = extract_page_metadata(html_content=r_html, url=curr_url)
                    r_content = extract_page_content(html_content=r_html, url=curr_url)
                    r_images = extract_page_images(html_content=r_html, url=curr_url)
                    r_resources = extract_page_links_and_resources(html_content=r_html, url=curr_url)
                    r_sd = extract_structured_data(html_content=r_html, url=curr_url)

                    rendered_evidence_dict = {
                        "title": r_meta["title"],
                        "meta_description": r_meta["meta_description"],
                        "word_count": r_content["word_count"],
                        "headings": r_content["headings"],
                        "paragraphs": r_content["paragraphs"],
                        "links": [l.model_dump() for l in r_resources["links"]],
                        "images": [i.model_dump() for i in r_images],
                        "structured_data": r_sd["summary"],
                    }

                    render_meta = RenderMetadata(
                        attempted=True,
                        rendered=True,
                        render_time_ms=render_result.render_time_ms,
                        final_url=render_result.final_url or final_url,
                        error=None,
                        reasons=render_decision.reasons,
                        browser_name=self.config.browser_type,
                        timeout=self.config.browser_page_timeout_seconds,
                    )

                    if r_content["word_count"] >= http_content["word_count"]:
                        final_title = r_meta["title"] or final_title
                        final_meta_desc = r_meta["meta_description"] or final_meta_desc
                        final_word_count = r_content["word_count"]
                        final_headings = r_content["headings"]
                        final_paragraphs = r_content["paragraphs"]
                        final_lists = r_content["lists"]
                        final_tables = r_content["tables"]
                        final_blockquotes = r_content["blockquotes"]
                        final_contacts = r_content["contacts"]
                        final_dates = r_content["dates"]

                    # DISCOVER NEW INTERNAL LINKS FROM RENDERED DOM
                    if curr_depth < self.config.max_depth:
                        for r_link in r_resources["links"]:
                            if r_link.is_internal:
                                add_to_inventory(
                                    r_link.href,
                                    depth=curr_depth + 1,
                                    parent_url=curr_url,
                                    anchor=r_link.anchor_text,
                                    discovery_method="browser_rendered_link",
                                )

                    # MERGE LINKS WITH PROVENANCE
                    http_href_map = {l.href: l for l in final_links}
                    for r_link in r_resources["links"]:
                        if r_link.href in http_href_map:
                            existing = http_href_map[r_link.href]
                            if "browser" not in existing.source_types:
                                existing.source_types.append("browser")
                        else:
                            r_link.source_types = ["browser"]
                            final_links.append(r_link)

                    # MERGE IMAGES WITH PROVENANCE
                    http_img_map = {i.src: i for i in final_images}
                    for r_img in r_images:
                        if r_img.src in http_img_map:
                            existing = http_img_map[r_img.src]
                            if "browser" not in existing.source_types:
                                existing.source_types.append("browser")
                        else:
                            r_img.source_types = ["browser"]
                            final_images.append(r_img)

                else:
                    render_meta = RenderMetadata(
                        attempted=True,
                        rendered=False,
                        render_time_ms=render_result.render_time_ms,
                        final_url=None,
                        error=render_result.error or "Browser rendering failed",
                        reasons=render_decision.reasons,
                        browser_name=self.config.browser_type,
                        timeout=self.config.browser_page_timeout_seconds,
                    )

            # Discover internal links from HTTP HTML if depth permits
            if curr_depth < self.config.max_depth:
                for link_ev in http_resources["links"]:
                    if link_ev.is_internal:
                        add_to_inventory(
                            link_ev.href,
                            depth=curr_depth + 1,
                            parent_url=curr_url,
                            anchor=link_ev.anchor_text,
                            discovery_method="html_link",
                        )

            heading_texts = [h["text"] for h in final_headings]
            role_signals = classify_page_role_signals(
                url=curr_url,
                title=final_title,
                headings=heading_texts,
                anchor_text=curr_anchor,
            )

            raw_text = final_paragraphs[0] if final_paragraphs else ""
            normalized_text = " ".join(final_paragraphs)
            collapsed, suspicious_toks = detect_word_boundary_collapse(normalized_text)
            extractability_info = {
                "raw_text_length": len(raw_text),
                "normalized_text_length": len(normalized_text),
                "word_boundary_collapse_detected": collapsed,
                "suspicious_tokens": suspicious_toks,
            }

            robots_meta = {
                "x_robots_tag": headers.get("x-robots-tag"),
            }

            internal_urls = sorted(list(set(l.href for l in final_links if l.is_internal)))
            external_urls = sorted(list(set(l.href for l in final_links if not l.is_internal)))

            page_ev = PageEvidence(
                url=curr_url,
                final_url=final_url,
                depth=curr_depth,
                status="success",
                status_code=status_code,
                content_type=headers.get("content-type", "text/html"),
                discovery_source=disc_method,
                title=final_title,
                meta_description=final_meta_desc,
                canonical_url=http_meta["canonical_url"],
                language=http_meta["language"],
                charset=http_meta.get("charset"),
                role_signals=role_signals,
                page_role=role_signals.classified_role,
                word_count=final_word_count,
                headings=final_headings,
                paragraphs=final_paragraphs,
                lists=final_lists,
                tables=final_tables,
                blockquotes=final_blockquotes,
                captions=http_content.get("captions", []),
                links=final_links,
                internal_links=internal_urls,
                external_links=external_urls,
                images=final_images,
                forms=final_forms,
                documents=final_documents,
                robots_directives=robots_meta,
                structured_data=final_sd["summary"],
                jsonld_raw_blocks=final_sd["jsonld_raw_blocks"],
                meta_tags=http_meta["meta_tags"],
                contacts=final_contacts,
                dates=final_dates,
                text_extractability=extractability_info,
                http_evidence=http_evidence_dict,
                rendered_evidence=rendered_evidence_dict,
                render_metadata=render_meta,
                html_content=html,
                headers=headers,
            )
            crawled_pages.append(page_ev)

        total_discovered = len(discovered_urls)
        total_crawled = len(crawled_pages)
        truncated = total_discovered > total_crawled
        truncation_reason = None
        if truncated:
            if total_crawled >= self.config.max_pages:
                truncation_reason = f"max_pages_limit_reached ({total_crawled}/{self.config.max_pages})"
            else:
                truncation_reason = "max_depth_reached"

        total_images = sum(len(p.images) for p in crawled_pages)
        total_pdf = sum(sum(1 for d in p.documents if d.file_type == "pdf") for p in crawled_pages)
        total_other_doc = sum(sum(1 for d in p.documents if d.file_type != "pdf") for p in crawled_pages)
        total_forms = sum(len(p.forms) for p in crawled_pages)

        resource_summary = {
            "html_pages": total_crawled,
            "images": total_images,
            "pdf_documents": total_pdf,
            "other_documents": total_other_doc,
            "forms": total_forms,
            "pages_browser_rendered": pages_rendered_count,
        }

        duration_sec = round(time.time() - start_time, 3)

        discovered_url_records = list(discovered_urls.values())

        website_evidence = WebsiteEvidence(
            start_url=norm_start,
            normalized_start_url=norm_start,
            crawl_metadata={
                "same_domain_only": self.config.same_domain_only,
                "user_agent": self.config.user_agent,
                "request_timeout_seconds": self.config.request_timeout_seconds,
                "duration_seconds": duration_sec,
                "browser_enabled": self.config.browser_enabled,
                "max_rendered_pages": self.config.max_rendered_pages,
            },
            robots=robots_evidence,
            sitemaps=sitemap_evidence_items,
            discovered_urls=discovered_url_records,
            crawled_pages=crawled_pages,
            failed_urls=failed_url_records,
            skipped_urls=skipped_urls,
            resource_summary=resource_summary,
            pages_discovered=total_discovered,
            pages_crawled=total_crawled,
            pages_rendered=pages_rendered_count,
            max_depth=self.config.max_depth,
            truncated=truncated,
            truncation_reason=truncation_reason,
        )

        manifest = CrawlManifest(
            start_url=norm_start,
            pages_discovered=total_discovered,
            pages_crawled=total_crawled,
            max_depth=self.config.max_depth,
            truncated=truncated,
            truncation_reason=truncation_reason,
            robots_status=robots_info,
            sitemap_status=sitemap_info,
            failed_urls=failed_urls_compat,
            skipped_urls=skipped_urls,
            pages=crawled_pages,
            website_evidence=website_evidence,
        )

        return manifest
"""

Path("src/crawler/engine.py").write_text(engine_code, encoding="utf-8")
print("Successfully wrote src/crawler/engine.py!")

