"""Extraction Manager - Master Coordinator for Step 2 Evidence Collection / Extraction.

Orchestrates all specialized modular extractors, enforces deterministic execution ordering,
manages centralized sequential Evidence ID assignment (EV-00001, EV-00002, ...),
preserves raw artifacts, tracks provenance, handles extractor failures gracefully,
and produces a canonical ExtractionResult.

This module strictly answers: "What exact evidence did we find?"
It contains NO audit findings, NO scores, NO recommendations, and NO LLM calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
if TYPE_CHECKING:
    from src.crawler.engine import CrawlManifest

from src.evidence.models import PageEvidence, WebsiteEvidence
from src.extraction.entity_extractor import EntityExtractor
from src.extraction.freshness_extractor import FreshnessExtractor
from src.extraction.http_extractor import HTTPExtractor
from src.extraction.id_generator import EvidenceIdGenerator
from src.extraction.link_extractor import LinkExtractor
from src.extraction.media_extractor import MediaExtractor
from src.extraction.metadata_extractor import MetadataExtractor
from src.extraction.resource_extractor import ResourceExtractor
from src.extraction.robots_extractor import RobotsExtractor
from src.extraction.schema_extractor import SchemaExtractor
from src.extraction.site_extractor import SiteExtractor
from src.extraction.text_extractor import TextExtractor
from src.shared.evidence_schema import (
    CanonicalEvidence,
    EvidenceType,
    ExtractionError,
    ExtractionResult,
    Provenance,
)


class ExtractionManager:
    """Master Extraction Coordinator normalizing raw crawler data into canonical Evidence items."""

    def __init__(self, id_prefix: str = "EV-", id_digits: int = 5):
        self.id_generator = EvidenceIdGenerator(prefix=id_prefix, digits=id_digits, start=1)
        self.http_extractor = HTTPExtractor()
        self.text_extractor = TextExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.schema_extractor = SchemaExtractor()
        self.robots_extractor = RobotsExtractor()
        self.freshness_extractor = FreshnessExtractor()
        self.entity_extractor = EntityExtractor()
        self.link_extractor = LinkExtractor()
        self.media_extractor = MediaExtractor()
        self.resource_extractor = ResourceExtractor()
        self.site_extractor = SiteExtractor()

    def extract(self, crawl_input: Union[CrawlManifest, WebsiteEvidence, Dict[str, Any]]) -> ExtractionResult:
        """Main extraction entrypoint converting crawler output into canonical, auditable Evidence objects."""
        start_time = time.time()
        self.id_generator.reset()

        raw_evidence_list: List[CanonicalEvidence] = []
        errors: List[ExtractionError] = []

        # 1. Normalize input into WebsiteEvidence or extracted dictionaries
        website_ev: Optional[WebsiteEvidence] = None
        pages: List[PageEvidence] = []
        start_url: str = ""
        discovered_urls_count: int = 0
        crawled_pages_count: int = 0
        max_depth: int = 3
        truncated: bool = False
        truncation_reason: Optional[str] = None
        resource_summary: Dict[str, Any] = {}
        failed_urls: List[Any] = []
        skipped_urls: List[Dict[str, Any]] = []
        crawl_metadata: Dict[str, Any] = {}

        if hasattr(crawl_input, "website_evidence") and hasattr(crawl_input, "start_url"):
            start_url = crawl_input.start_url
            pages = crawl_input.pages
            discovered_urls_count = crawl_input.pages_discovered
            crawled_pages_count = crawl_input.pages_crawled
            max_depth = crawl_input.max_depth
            truncated = crawl_input.truncated
            truncation_reason = crawl_input.truncation_reason
            failed_urls = crawl_input.failed_urls
            skipped_urls = crawl_input.skipped_urls
            website_ev = crawl_input.website_evidence
            if website_ev:
                resource_summary = website_ev.resource_summary
                crawl_metadata = website_ev.crawl_metadata
        elif isinstance(crawl_input, WebsiteEvidence):
            website_ev = crawl_input
            start_url = crawl_input.start_url
            pages = crawl_input.pages
            discovered_urls_count = crawl_input.pages_discovered
            crawled_pages_count = crawl_input.pages_crawled
            max_depth = crawl_input.max_depth
            truncated = crawl_input.truncated
            truncation_reason = crawl_input.truncation_reason
            failed_urls = crawl_input.failed_urls
            skipped_urls = crawl_input.skipped_urls
            resource_summary = crawl_input.resource_summary
            crawl_metadata = crawl_input.crawl_metadata
        elif isinstance(crawl_input, dict):
            start_url = crawl_input.get("start_url", "")
            raw_pages = crawl_input.get("pages") or crawl_input.get("crawled_pages") or []
            pages = [PageEvidence(**p) if isinstance(p, dict) else p for p in raw_pages]
            discovered_urls_count = crawl_input.get("pages_discovered", len(pages))
            crawled_pages_count = crawl_input.get("pages_crawled", len(pages))
            max_depth = crawl_input.get("max_depth", 3)
            truncated = crawl_input.get("truncated", False)
            truncation_reason = crawl_input.get("truncation_reason")
            resource_summary = crawl_input.get("resource_summary", {})
            failed_urls = crawl_input.get("failed_urls", [])
            skipped_urls = crawl_input.get("skipped_urls", [])
            crawl_metadata = crawl_input.get("crawl_metadata", {})
            if "robots" in crawl_input:
                try:
                    r_raw = crawl_input["robots"]
                    r_ev = r_raw if isinstance(r_raw, WebsiteEvidence) else WebsiteEvidence(**crawl_input).robots
                except Exception:
                    pass

        # -------------------------------------------------------------
        # STEP 1: SITENIDE ROBOTS.TXT & SITEMAPS / MACHINE RESOURCES
        # -------------------------------------------------------------
        if website_ev and website_ev.robots:
            try:
                r_evs = self.robots_extractor.extract_robots_evidence(robots_evidence=website_ev.robots)
                raw_evidence_list.extend(r_evs)
            except Exception as r_err:
                errors.append(ExtractionError(extractor="robots-extractor", source=website_ev.robots.url, error=str(r_err)))

        if website_ev and website_ev.sitemaps:
            try:
                sm_evs = self.resource_extractor.extract_sitemap_evidence(sitemaps=website_ev.sitemaps)
                raw_evidence_list.extend(sm_evs)
            except Exception as sm_err:
                errors.append(ExtractionError(extractor="resource-extractor", source="sitemaps", error=str(sm_err)))

        # -------------------------------------------------------------
        # STEP 2: PER-PAGE EVIDENCE EXTRACTION (DETERMINISTIC SEQUENCE)
        # -------------------------------------------------------------
        for page in pages:
            page_url = page.url
            html_raw = page.html_content
            headers_raw = page.headers

            # 2a. Raw HTML & Rendered DOM Evidence
            if html_raw is not None:
                raw_evidence_list.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.RAW_HTML,
                        source="raw_html",
                        url=page_url,
                        data={"html_content": html_raw, "length": len(html_raw)},
                        provenance=Provenance(
                            source="crawler.response.html",
                            extraction_method="direct-field",
                            url=page_url,
                            location="<!DOCTYPE html>",
                        ),
                        is_raw=True,
                    )
                )

            # Record render artifact state (if client-side rendering was evaluated/available)
            raw_evidence_list.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.RENDER_ARTIFACT,
                    source="crawler_render",
                    url=page_url,
                    data={"rendered_dom_available": False, "render_engine": "static_http"},
                    provenance=Provenance(
                        source="crawler.render_engine",
                        extraction_method="direct-field",
                        url=page_url,
                        location="render:artifact",
                    ),
                )
            )

            # 2b. HTTP Status & Headers Extractor
            try:
                http_evs = self.http_extractor.extract_http_evidence(
                    requested_url=page_url,
                    final_url=page.final_url,
                    status_code=page.status_code,
                    headers=headers_raw,
                    content_type=page.content_type,
                )
                raw_evidence_list.extend(http_evs)
            except Exception as h_err:
                errors.append(ExtractionError(extractor="http-extractor", source=page_url, error=str(h_err)))

            # 2c. Metadata Extractor
            try:
                meta_evs = self.metadata_extractor.extract_metadata_evidence(
                    url=page_url,
                    html_content=html_raw,
                    title=page.title,
                    meta_description=page.meta_description,
                    canonical_url=page.canonical_url,
                    language=page.language,
                    charset=page.charset,
                    meta_tags=page.meta_tags,
                    robots_directives=page.robots_directives,
                )
                raw_evidence_list.extend(meta_evs)
            except Exception as m_err:
                errors.append(ExtractionError(extractor="metadata-extractor", source=page_url, error=str(m_err)))

            # 2d. Text & Structure Extractor
            try:
                text_evs = self.text_extractor.extract_text_evidence(
                    url=page_url,
                    html_content=html_raw,
                    headings=page.headings,
                    paragraphs=page.paragraphs,
                    lists=page.lists,
                    tables=page.tables,
                    blockquotes=page.blockquotes,
                    captions=page.captions,
                    word_count=page.word_count,
                    text_extractability=page.text_extractability,
                )
                raw_evidence_list.extend(text_evs)
            except Exception as t_err:
                errors.append(ExtractionError(extractor="text-extractor", source=page_url, error=str(t_err)))

            # 2e. Schema.org & Semantic Markup Extractor
            try:
                schema_evs = self.schema_extractor.extract_schema_evidence(
                    url=page_url,
                    html_content=html_raw,
                    jsonld_raw_blocks=page.jsonld_raw_blocks,
                    structured_data_summary=page.structured_data,
                )
                raw_evidence_list.extend(schema_evs)
            except Exception as s_err:
                errors.append(ExtractionError(extractor="schema-extractor", source=page_url, error=str(s_err)))

            # 2f. Freshness & Temporal Date Extractor
            try:
                fresh_evs = self.freshness_extractor.extract_freshness_evidence(
                    url=page_url,
                    headers=headers_raw,
                    meta_tags=page.meta_tags,
                    date_evidence=page.dates,
                )
                raw_evidence_list.extend(fresh_evs)
            except Exception as f_err:
                errors.append(ExtractionError(extractor="freshness-extractor", source=page_url, error=str(f_err)))

            # 2g. Entity Identity Extractor
            try:
                entity_evs = self.entity_extractor.extract_entity_evidence(
                    url=page_url,
                    contacts=page.contacts,
                    meta_tags=page.meta_tags,
                    links=page.links,
                )
                raw_evidence_list.extend(entity_evs)
            except Exception as e_err:
                errors.append(ExtractionError(extractor="entity-extractor", source=page_url, error=str(e_err)))

            # 2h. Link & Resource Extractor
            try:
                link_evs = self.link_extractor.extract_link_evidence(
                    url=page_url,
                    html_content=html_raw,
                    links=page.links,
                    documents=page.documents,
                )
                raw_evidence_list.extend(link_evs)
            except Exception as l_err:
                errors.append(ExtractionError(extractor="link-extractor", source=page_url, error=str(l_err)))

            # 2i. Media & Form Extractor
            try:
                media_evs = self.media_extractor.extract_media_evidence(
                    url=page_url,
                    html_content=html_raw,
                    images=page.images,
                    forms=page.forms,
                )
                raw_evidence_list.extend(media_evs)
            except Exception as med_err:
                errors.append(ExtractionError(extractor="media-extractor", source=page_url, error=str(med_err)))

        # -------------------------------------------------------------
        # STEP 3: SITEWIDE COVERAGE, LIMITS & FAILURE STATISTICS
        # -------------------------------------------------------------
        try:
            site_evs = self.site_extractor.extract_site_evidence(
                start_url=start_url,
                pages_discovered=discovered_urls_count,
                pages_crawled=crawled_pages_count,
                max_depth=max_depth,
                truncated=truncated,
                truncation_reason=truncation_reason,
                resource_summary=resource_summary,
                failed_urls=failed_urls,
                skipped_urls=skipped_urls,
                crawl_metadata=crawl_metadata,
            )
            raw_evidence_list.extend(site_evs)
        except Exception as site_err:
            errors.append(ExtractionError(extractor="site-extractor", source=start_url, error=str(site_err)))

        # -------------------------------------------------------------
        # STEP 4: DEDUPLICATION & CENTRALIZED EVIDENCE ID ASSIGNMENT
        # -------------------------------------------------------------
        final_evidence_list: List[CanonicalEvidence] = []
        seen_keys = set()

        for ev in raw_evidence_list:
            # Create a signature key based on type, url, normalized data, and provenance source
            # Preserves multi-source independence (e.g. Org name from JSON-LD vs Org name from DOM text)
            data_repr = str(sorted(ev.data.items())) if isinstance(ev.data, dict) else str(ev.data)
            sig_key = (str(ev.type), ev.url or "", ev.provenance.source, ev.provenance.location or "", data_repr)

            if sig_key in seen_keys and not ev.is_raw:
                continue
            seen_keys.add(sig_key)

            # Assign sequential deterministic ID
            ev.id = self.id_generator.next_id()
            final_evidence_list.append(ev)

        duration_sec = round(time.time() - start_time, 4)
        metadata = {
            "total_evidence_count": len(final_evidence_list),
            "errors_count": len(errors),
            "pages_processed": len(pages),
            "duration_seconds": duration_sec,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return ExtractionResult(
            evidence=final_evidence_list,
            errors=errors,
            metadata=metadata,
        )
