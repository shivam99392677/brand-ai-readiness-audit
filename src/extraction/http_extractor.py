"""HTTP Evidence Extractor.

Normalizes HTTP status, redirect chains, raw headers, and individual header signals.
This module is strictly an objective evidence extractor and does NOT evaluate status or header validity.
"""

from typing import Any, Dict, List, Optional
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class HTTPExtractor:
    """Extracts factual HTTP response signals, status codes, headers, and redirect chains."""

    IMPORTANT_HEADERS = [
        "content-type",
        "content-encoding",
        "cache-control",
        "etag",
        "last-modified",
        "location",
        "x-robots-tag",
        "vary",
        "server",
        "content-language",
        "link",
        "strict-transport-security",
        "access-control-allow-origin",
    ]

    def extract_http_evidence(
        self,
        requested_url: str,
        final_url: Optional[str] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        redirect_chain: Optional[List[Dict[str, Any]]] = None,
        response_time_ms: Optional[float] = None,
        content_type: Optional[str] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized HTTP evidence items from crawl response."""
        evidence_items: List[CanonicalEvidence] = []
        raw_headers = headers or {}
        normalized_headers = {k.lower().strip(): v.strip() for k, v in raw_headers.items()}
        effective_final_url = final_url or requested_url

        # 1. HTTP Status Code Evidence
        status_data = {
            "requested_url": requested_url,
            "final_url": effective_final_url,
            "status_code": status_code,
            "is_success": 200 <= status_code < 300,
            "is_redirect": 300 <= status_code < 400,
            "is_client_error": 400 <= status_code < 500,
            "is_server_error": 500 <= status_code < 600,
        }
        evidence_items.append(
            CanonicalEvidence(
                id="",  # ID assigned centrally by ExtractionManager
                type=EvidenceType.HTTP_STATUS,
                source="http_response",
                url=requested_url,
                data=status_data,
                provenance=Provenance(
                    source="crawler.response.status",
                    extraction_method="direct-field",
                    url=requested_url,
                    location="http:status_code",
                ),
            )
        )

        # 2. Redirect Chain Evidence (if redirects occurred)
        if redirect_chain:
            for idx, r in enumerate(redirect_chain):
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.HTTP_REDIRECT,
                        source="http_response",
                        url=requested_url,
                        data={
                            "hop_index": idx,
                            "from_url": r.get("from_url", requested_url),
                            "to_url": r.get("to_url", effective_final_url),
                            "status_code": r.get("status_code", 301),
                        },
                        provenance=Provenance(
                            source="crawler.response.redirects",
                            extraction_method="direct-field",
                            url=requested_url,
                            location=f"redirect_hop:{idx}",
                        ),
                    )
                )
        elif effective_final_url != requested_url:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.HTTP_REDIRECT,
                    source="http_response",
                    url=requested_url,
                    data={
                        "from_url": requested_url,
                        "to_url": effective_final_url,
                        "status_code": status_code if 300 <= status_code < 400 else 302,
                    },
                    provenance=Provenance(
                        source="crawler.response.url",
                        extraction_method="direct-field",
                        url=requested_url,
                        location="http:final_url",
                    ),
                )
            )

        # 3. Raw Headers Envelope Evidence
        if normalized_headers:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.RAW_HEADERS,
                    source="http_response",
                    url=requested_url,
                    data={"headers": normalized_headers},
                    provenance=Provenance(
                        source="crawler.response.headers",
                        extraction_method="direct-field",
                        url=requested_url,
                        location="http:headers",
                    ),
                    is_raw=True,
                )
            )

        # 4. Individual Header Evidence for AI/Crawlability/Freshness/Security Signals
        for name, value in normalized_headers.items():
            # Include all important headers or specific AI tags
            if name in self.IMPORTANT_HEADERS or name.startswith("x-") or name.startswith("cf-"):
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.HTTP_HEADER,
                        source="http_response",
                        url=requested_url,
                        data={
                            "name": name,
                            "value": value,
                        },
                        provenance=Provenance(
                            source="crawler.response.headers",
                            extraction_method="header-inspection",
                            url=requested_url,
                            location=f"header:{name}",
                        ),
                    )
                )

        # 5. Content-Type fallback if not in headers dict
        if content_type and "content-type" not in normalized_headers:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.HTTP_HEADER,
                    source="http_response",
                    url=requested_url,
                    data={"name": "content-type", "value": content_type},
                    provenance=Provenance(
                        source="crawler.response.content_type",
                        extraction_method="direct-field",
                        url=requested_url,
                        location="header:content-type",
                    ),
                )
            )

        # 6. Response Timing Evidence
        if response_time_ms is not None:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.RESPONSE_TIMING,
                    source="http_response",
                    url=requested_url,
                    data={"response_time_ms": round(float(response_time_ms), 2)},
                    provenance=Provenance(
                        source="crawler.response.timing",
                        extraction_method="direct-field",
                        url=requested_url,
                        location="http:timing",
                    ),
                )
            )

        return evidence_items
