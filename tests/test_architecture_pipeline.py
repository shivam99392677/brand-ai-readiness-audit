"""Integration tests for Target Architecture: One Crawl, Shared Evidence, and Orchestration."""

import json
import pytest

from src.crawler.engine import CrawlConfig, SiteCrawler
from src.evidence.models import WebsiteEvidence
from src.orchestrator import AuditOrchestrator, validate_target_url


SAMPLE_SITE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Brand AI Readiness Showcase</title>
    <meta name="description" content="Auditing digital presence for Generative Engine Optimization.">
    <link rel="canonical" href="https://showcase.example.com/">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Brand AI Readiness Showcase",
        "url": "https://showcase.example.com/"
    }
    </script>
</head>
<body>
    <h1>Brand AI Readiness Showcase</h1>
    <p>We provide machine-readable brand data for AI models and web crawlers.</p>
    <img src="/assets/hero.jpg" alt="Showcase Hero" width="1200" height="800" />
    <a href="/about">About Us</a>
    <a href="/contact">Contact Us</a>
</body>
</html>
"""

ABOUT_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>About Us — Showcase</title>
</head>
<body>
    <h1>About Our Brand</h1>
    <p>Founded in 2026 to pioneer evidence-first AI readiness auditing.</p>
    <a href="/">Back to Home</a>
</body>
</html>
"""


def test_single_crawl_shared_evidence_flow():
    fetch_counts = {"count": 0}

    def mock_fetcher(target_url: str):
        fetch_counts["count"] += 1
        if "about" in target_url:
            return 200, ABOUT_PAGE_HTML, {"content-type": "text/html"}
        return 200, SAMPLE_SITE_HTML, {"content-type": "text/html"}

    config = CrawlConfig(max_pages=2, max_depth=2, respect_robots=False, discover_sitemap=False)
    orchestrator = AuditOrchestrator(crawl_config=config)

    report = orchestrator.execute_audit(
        target_url="https://showcase.example.com/",
        custom_fetcher=mock_fetcher,
    )

    # Verify single crawl fetch executed once per discovered URL
    assert fetch_counts["count"] == 2
    assert report.url == "https://showcase.example.com/"
    assert len(report.skills_run) == 6
    assert "crawl-render-audit" in report.skills_run
    assert "structured-data-audit" in report.skills_run
    assert "fact-quality-audit" in report.skills_run
    assert "freshness-corroboration" in report.skills_run
    assert "entity-identity-audit" in report.skills_run
    assert "engagement-audit" in report.skills_run

    # Verify shared evidence store structure
    assert report.crawl is not None
    assert report.crawl["pages_crawled"] == 2
    assert report.crawl["pages_discovered"] == 3

    # Check rich WebsiteEvidence store
    web_ev = report.crawl.get("website_evidence")
    assert web_ev is not None
    assert len(web_ev["pages"]) == 2
    
    # Check page evidence general extraction
    p1 = web_ev["pages"][0]
    assert p1["title"] == "Brand AI Readiness Showcase"
    assert len(p1["images"]) == 1
    assert p1["images"][0]["alt"] == "Showcase Hero"
    assert len(p1["links"]) == 2

    # Verify JSON serializability
    dumped_json = json.dumps(report.model_dump())
    assert isinstance(dumped_json, str)
    assert "Brand AI Readiness Showcase" in dumped_json
