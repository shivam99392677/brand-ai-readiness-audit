"""Audit Orchestrator - Master Entrypoint coordinating crawler, ExtractionManager, 6 analysis skills, and Adobe Report Composer."""

import argparse
import json
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from src.analysis.crawl_render_audit import run_crawl_render_audit
from src.analysis.engagement_audit import run_engagement_audit
from src.analysis.entity_identity_audit import run_entity_identity_audit
from src.analysis.fact_quality_audit import run_fact_quality_audit
from src.analysis.freshness_corroboration import run_freshness_corroboration
from src.analysis.structured_data_audit import run_structured_data_audit
from src.analysis.sitemap_audit import run_sitemap_audit
from src.analysis.bot_block_audit import run_bot_block_audit
from src.crawler.engine import CrawlConfig, CrawlManifest, SiteCrawler
from src.extraction.extraction_manager import ExtractionManager
from src.models import (
    AuditReport,
    Evidence,
    Finding,
    FindingSeverity,
    FindingStatus,
)
from src.reporting.composer import compose_adobe_report, save_adobe_report
from src.shared.evidence_schema import ExtractionResult


def validate_target_url(url: str) -> str:
    """Validates that the provided target URL is structured correctly."""
    if not url or not isinstance(url, str):
        raise ValueError("Target URL must be a non-empty string.")
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid target URL '{url}'. URL must include http:// or https:// scheme and domain.")
    return cleaned



# Core skills (original six) that are always run by default
CORE_SKILL_REGISTRY: Dict[str, Callable[..., List[Finding]]] = {
    "crawl-render-audit": run_crawl_render_audit,
    "structured-data-audit": run_structured_data_audit,
    "fact-quality-audit": run_fact_quality_audit,
    "freshness-corroboration": run_freshness_corroboration,
    "entity-identity-audit": run_entity_identity_audit,
    "engagement-audit": run_engagement_audit,
}

# Extended skills (optional)
EXTENDED_SKILL_REGISTRY: Dict[str, Callable[..., List[Finding]]] = {
    "sitemap-audit": run_sitemap_audit,
    "bot-block-audit": run_bot_block_audit,
}

# Default registry used when no custom registry is provided
DEFAULT_SKILL_REGISTRY = CORE_SKILL_REGISTRY.copy()


class AuditOrchestrator:
    """Master Entrypoint Orchestrator coordinating site-wide discovery, extraction, and 6 specialized audit skills."""

    def __init__(
        self,
        skill_registry: Optional[Dict[str, Callable[..., List[Finding]]]] = None,
        crawl_config: Optional[CrawlConfig] = None,
        enable_extended_skills: bool = False,
    ):
        # Determine which registry to use
        if skill_registry is not None:
            self.skill_registry = skill_registry
        else:
            if enable_extended_skills:
                # Merge core and extended skills
                merged = CORE_SKILL_REGISTRY.copy()
                merged.update(EXTENDED_SKILL_REGISTRY)
                self.skill_registry = merged
            else:
                self.skill_registry = CORE_SKILL_REGISTRY.copy()
        self.crawl_config = crawl_config or CrawlConfig()
        self.crawler = SiteCrawler(config=self.crawl_config)
        self.extraction_manager = ExtractionManager()

    def execute_audit(
        self,
        target_url: str,
        html_override: Optional[str] = None,
        headers_override: Optional[Dict[str, str]] = None,
        status_code_override: Optional[int] = None,
        custom_fetcher: Optional[Callable[[str], tuple]] = None,
        output_file: Optional[str] = None,
    ) -> AuditReport:
        """Executes site-wide discovery, bounded crawl, evidence extraction, 6 sub-skills, and Adobe report synthesis."""
        valid_url = validate_target_url(target_url)

        # 1. Execute site-wide discovery & crawl
        crawl_manifest = self.crawler.crawl_site(
            start_url=valid_url,
            html_override=html_override,
            custom_fetcher=custom_fetcher,
        )

        # 2. Execute General Evidence Extraction Layer
        extraction_result: ExtractionResult = self.extraction_manager.extract(crawl_manifest)

        # Get primary homepage metadata for backward-compatibility fallbacks
        primary_page = next((p for p in crawl_manifest.pages if p.url == valid_url or p.depth == 0), None)
        if primary_page:
            html_content = primary_page.html_content
            response_headers = primary_page.headers or headers_override or {}
            status_code = primary_page.status_code or status_code_override or 200
        else:
            html_content = html_override or ""
            response_headers = headers_override or {}
            status_code = status_code_override or 200

        skills_run: List[str] = []
        all_findings: List[Finding] = []

        # 3. Delegate execution to all 6 registered analysis skills consuming full evidence
        for skill_id, skill_fn in self.skill_registry.items():
            skills_run.append(skill_id)
            try:
                # Try canonical signature (evidence=extraction_result, website=crawl_manifest.website_evidence)
                try:
                    findings = skill_fn(
                        evidence=extraction_result,
                        website=crawl_manifest.website_evidence,
                    )
                except TypeError:
                    # Fallback to legacy signature for custom wrapped skills
                    try:
                        findings = skill_fn(
                            url=valid_url,
                            html=html_content,
                            headers=response_headers,
                            status_code=status_code,
                            crawl_manifest=crawl_manifest,
                        )
                    except TypeError:
                        findings = skill_fn(
                            url=valid_url,
                            html=html_content,
                            headers=response_headers,
                            status_code=status_code,
                        )

                if isinstance(findings, list):
                    all_findings.extend(findings)
            except Exception as skill_err:
                err_ev = Evidence(
                    source_url=valid_url,
                    evidence_type="skill_execution_error",
                    observed={
                        "error_type": type(skill_err).__name__,
                        "error_message": str(skill_err),
                    },
                    location=f"skill:{skill_id}",
                )
                err_finding = Finding(
                    skill=skill_id,
                    check_id=f"{skill_id.upper().replace('-', '_')}_ERR",
                    title=f"Skill Execution Error ({skill_id})",
                    status=FindingStatus.ERROR,
                    severity=FindingSeverity.HIGH,
                    description=f"Skill '{skill_id}' encountered an error during execution: {str(skill_err)}",
                    evidence=[err_ev],
                    recommendation=f"Inspect execution logic for skill '{skill_id}'.",
                )
                all_findings.append(err_finding)

        # 4. Compose Adobe Report JSON
        adobe_report = compose_adobe_report(target_url=valid_url, findings=all_findings)
        if output_file:
            save_adobe_report(adobe_report, filepath=output_file)

        # 5. Synthesize final AuditReport
        report = AuditReport.create(
            url=valid_url,
            crawl=crawl_manifest.model_dump(),
            skills_run=skills_run,
            findings=all_findings,
        )

        return report


def main():
    parser = argparse.ArgumentParser(description="Brand AI Readiness Audit Orchestrator CLI")
    parser.add_argument("url", help="Single target URL to audit (e.g. https://example.com)")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum pages to crawl")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum crawl depth")
    parser.add_argument("--output", "-o", default="report.json", help="Path to save Adobe report.json")
    args = parser.parse_args()

    config = CrawlConfig(max_pages=args.max_pages, max_depth=args.max_depth)
    orchestrator = AuditOrchestrator(crawl_config=config)
    report = orchestrator.execute_audit(target_url=args.url, output_file=args.output)
    
    # Also print the Adobe format report to stdout
    adobe_rep = compose_adobe_report(target_url=args.url, findings=report.findings)
    print(json.dumps(adobe_rep, indent=2))


if __name__ == "__main__":
    main()
