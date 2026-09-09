"""Robots.txt Evidence Extractor.

Extracts raw robots.txt artifacts, parsed user-agent rule groups,
AI crawler-specific directives (GPTBot, ClaudeBot, PerplexityBot, Bytespider, Google-Extended, *),
Crawl-delay parameters, sitemap declarations, and syntax warnings.
This module is strictly factual and does NOT make pass/fail judgments about bot blocking.
"""

from typing import Any, Dict, List, Optional
from src.crawler.robots import parse_robots_txt_rules
from src.evidence.models import RobotsEvidence, UserAgentRuleGroup
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance

AI_USER_AGENTS = [
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "PerplexityBot",
    "Bytespider",
    "Google-Extended",
    "CCBot",
    "cohere-ai",
    "Diffbot",
    "FacebookBot",
    "*",
]


class RobotsExtractor:
    """Extracts factual robots.txt rules, raw files, and sitemap declarations."""

    def extract_robots_evidence(
        self,
        robots_evidence: Optional[RobotsEvidence] = None,
        raw_robots_content: Optional[str] = None,
        robots_url: str = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized robots.txt evidence items."""
        evidence_items: List[CanonicalEvidence] = []
        target_url = robots_url or (robots_evidence.url if robots_evidence else "")

        # 1. Raw Robots.txt Content Artifact (if available)
        if raw_robots_content is not None:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.RAW_ROBOTS,
                    source="robots_txt",
                    url=target_url,
                    data={
                        "raw_content": raw_robots_content,
                        "length": len(raw_robots_content),
                        "status_code": status_code,
                    },
                    provenance=Provenance(
                        source="crawler.robots_fetch",
                        extraction_method="direct-field",
                        url=target_url,
                        location="/robots.txt",
                    ),
                    is_raw=True,
                )
            )

        # 2. Parse rules if raw_content available, else use robots_evidence
        groups: List[UserAgentRuleGroup] = []
        sitemaps: List[str] = []
        parse_errors: List[str] = []
        status = status_code

        if raw_robots_content:
            parsed_groups, sitemaps, _, _, _ = parse_robots_txt_rules(raw_robots_content)
            groups = parsed_groups
            source_desc = "raw_robots_content"
            method_desc = "robots-parser"
        elif robots_evidence:
            groups = robots_evidence.user_agent_groups
            sitemaps = robots_evidence.sitemaps_declared
            parse_errors = robots_evidence.parse_errors
            status = robots_evidence.status_code
            source_desc = "crawler.robots_evidence"
            method_desc = "direct-field"
        else:
            return evidence_items

        # 3. HTTP Availability Status Evidence
        evidence_items.append(
            CanonicalEvidence(
                id="",
                type=EvidenceType.HTTP_STATUS,
                source="robots_txt",
                url=target_url,
                data={
                    "resource": "robots.txt",
                    "status_code": status,
                    "available": status == 200,
                    "groups_count": len(groups),
                    "sitemaps_declared_count": len(sitemaps),
                },
                provenance=Provenance(
                    source="crawler.robots_fetch",
                    extraction_method="direct-field",
                    url=target_url,
                    location="http:status_code",
                ),
            )
        )

        # 4. Parsed User-Agent Rule Directives Evidence
        for g_idx, group in enumerate(groups):
            ua_list = group.user_agents or [group.user_agent] if hasattr(group, "user_agent") else ["*"]
            
            # Record individual Allow rules
            for allow_path in group.allow:
                for ua in ua_list:
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.ROBOTS_RULE,
                            source="robots_txt",
                            url=target_url,
                            data={
                                "user_agent": ua,
                                "directive": "Allow",
                                "path": allow_path,
                                "group_index": g_idx,
                            },
                            provenance=Provenance(
                                source=source_desc,
                                extraction_method=method_desc,
                                url=target_url,
                                location=f"User-agent:{ua} > Allow:{allow_path}",
                            ),
                        )
                    )

            # Record individual Disallow rules
            for disallow_path in group.disallow:
                for ua in ua_list:
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.ROBOTS_RULE,
                            source="robots_txt",
                            url=target_url,
                            data={
                                "user_agent": ua,
                                "directive": "Disallow",
                                "path": disallow_path,
                                "group_index": g_idx,
                            },
                            provenance=Provenance(
                                source=source_desc,
                                extraction_method=method_desc,
                                url=target_url,
                                location=f"User-agent:{ua} > Disallow:{disallow_path}",
                            ),
                        )
                    )

            # Record Crawl-Delay if present
            if group.crawl_delay is not None:
                for ua in ua_list:
                    evidence_items.append(
                        CanonicalEvidence(
                            id="",
                            type=EvidenceType.ROBOTS_CRAWL_DELAY,
                            source="robots_txt",
                            url=target_url,
                            data={
                                "user_agent": ua,
                                "crawl_delay_seconds": group.crawl_delay,
                                "group_index": g_idx,
                            },
                            provenance=Provenance(
                                source=source_desc,
                                extraction_method=method_desc,
                                url=target_url,
                                location=f"User-agent:{ua} > Crawl-delay:{group.crawl_delay}",
                            ),
                        )
                    )

        # 5. Sitemap Declarations in robots.txt
        for s_url in sitemaps:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.ROBOTS_SITEMAP_DECLARATION,
                    source="robots_txt",
                    url=target_url,
                    data={"declared_sitemap_url": s_url},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=target_url,
                        location=f"Sitemap:{s_url}",
                    ),
                )
            )

        # 6. Robots Parse Errors / Warnings
        for p_err in parse_errors:
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.ROBOTS_PARSE_ERROR,
                    source="robots_txt",
                    url=target_url,
                    data={"error": p_err},
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=target_url,
                        location="robots_txt:parse_error",
                    ),
                )
            )

        return evidence_items
