"""Sitewide Crawl and Coverage Evidence Extractor.

Extracts site-level inventory bounds, crawl truncation metadata, resource summaries,
and failed/skipped URL records.
This module is strictly factual and preserves complete visibility into crawl completeness.
"""

from typing import Any, Dict, List, Optional
from src.evidence.models import FailedURLEvidence, WebsiteEvidence
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class SiteExtractor:
    """Extracts factual site-level crawl bounds, inventory counts, and fetch error records."""

    def extract_site_evidence(
        self,
        start_url: str,
        pages_discovered: int = 0,
        pages_crawled: int = 0,
        max_depth: int = 3,
        truncated: bool = False,
        truncation_reason: Optional[str] = None,
        resource_summary: Optional[Dict[str, Any]] = None,
        failed_urls: Optional[List[Any]] = None,
        skipped_urls: Optional[List[Dict[str, Any]]] = None,
        crawl_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized sitewide evidence items."""
        evidence_items: List[CanonicalEvidence] = []

        # 1. Crawl Coverage and Truncation Evidence
        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.CRAWL_COVERAGE,
                source="crawler_manifest",
                url=start_url,
                data={
                    "start_url": start_url,
                    "pages_discovered": pages_discovered,
                    "pages_crawled": pages_crawled,
                    "max_depth": max_depth,
                    "truncated": truncated,
                    "truncation_reason": truncation_reason,
                    "crawl_metadata": crawl_metadata or {},
                },
                provenance=Provenance(
                    source="crawler.manifest.coverage",
                    extraction_method="direct-field",
                    url=start_url,
                    location="manifest:coverage",
                ),
            )
        )

        # 2. Resource Summary Evidence
        if resource_summary:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.CRAWL_RESOURCE_SUMMARY,
                    source="crawler_manifest",
                    url=start_url,
                    data=resource_summary,
                    provenance=Provenance(
                        source="crawler.manifest.resources",
                        extraction_method="direct-field",
                        url=start_url,
                        location="manifest:resource_summary",
                    ),
                )
            )

        # 3. Failed URLs Evidence
        if failed_urls:
            for idx, f in enumerate(failed_urls):
                if isinstance(f, FailedURLEvidence):
                    f_url = f.url
                    f_status = f.status_code
                    f_reason = f.error_reason
                    f_from = f.discovered_from
                    f_anchor = f.anchor_text
                    f_method = f.discovery_method
                elif isinstance(f, dict):
                    f_url = f.get("url", "")
                    f_status = f.get("status_code", 0)
                    f_reason = f.get("error_reason") or f.get("error", "fetch_failed")
                    f_from = f.get("discovered_from")
                    f_anchor = f.get("anchor_text")
                    f_method = f.get("discovery_method", "html_link")
                else:
                    continue

                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.FAILED_URL_RECORD,
                        source="crawler_manifest",
                        url=f_url,
                        data={
                            "url": f_url,
                            "status_code": f_status,
                            "error_reason": f_reason,
                            "discovered_from": f_from,
                            "anchor_text": f_anchor,
                            "discovery_method": f_method,
                            "order_index": idx,
                        },
                        provenance=Provenance(
                            source="crawler.failed_urls",
                            extraction_method="direct-field",
                            url=f_url,
                            location=f"failed_urls[{idx}]",
                        ),
                    )
                )

        # 4. Skipped URLs Evidence
        if skipped_urls:
            for s_idx, s in enumerate(skipped_urls):
                s_url = s.get("url", "")
                s_reason = s.get("reason", "unknown")
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.SKIPPED_URL_RECORD,
                        source="crawler_manifest",
                        url=s_url,
                        data={
                            "url": s_url,
                            "reason": s_reason,
                            "order_index": s_idx,
                        },
                        provenance=Provenance(
                            source="crawler.skipped_urls",
                            extraction_method="direct-field",
                            url=s_url,
                            location=f"skipped_urls[{s_idx}]",
                        ),
                    )
                )

        return evidence_items
