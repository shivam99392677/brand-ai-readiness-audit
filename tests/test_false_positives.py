"""Regression tests specifically verifying the elimination of false positives across analysis skills and Adobe report composition."""

import pytest
from src.analysis.structured_data_audit import run_structured_data_audit, audit_structured_data
from src.analysis.engagement_audit import run_engagement_audit
from src.analysis.freshness_corroboration import run_freshness_corroboration
from src.reporting.composer import AdobeReportComposer
from src.extraction.extraction_manager import ExtractionManager
from src.models import Finding, FindingStatus, FindingSeverity, Evidence
from src.evidence.models import WebsiteEvidence, PageEvidence, RobotsEvidence, LinkEvidence


def create_mock_extraction_result(pages_data, target_url="https://example.com"):
    """Helper to build ExtractionResult and WebsiteEvidence."""
    pages = []
    for pd in pages_data:
        p_url = pd.get("url", target_url)
        raw_links = pd.get("links", [])
        parsed_links = []
        for l in raw_links:
            if isinstance(l, dict):
                parsed_links.append(LinkEvidence(
                    href=l.get("href", ""),
                    source_page=p_url,
                    anchor_text=l.get("text", "")
                ))
            else:
                parsed_links.append(l)

        raw_json_ld = pd.get("jsonld_raw_blocks", [])
        p = PageEvidence(
            url=p_url,
            final_url=pd.get("final_url", p_url),
            status_code=pd.get("status_code", 200),
            title=pd.get("title", "Test Title"),
            headings=pd.get("headings", []),
            paragraphs=pd.get("paragraphs", []),
            links=parsed_links,
            images=pd.get("images", []),
            jsonld_raw_blocks=raw_json_ld,
            structured_data={"raw_blocks": raw_json_ld},
            meta_tags=pd.get("meta_tags", []),
            raw_html=pd.get("raw_html", ""),
            rendered_html=pd.get("rendered_html", ""),
            visible_text=pd.get("visible_text", " ".join(pd.get("paragraphs", []))),
        )
        pages.append(p)

    robots = RobotsEvidence(url=f"{target_url}/robots.txt", available=True, status_code=200)
    web_evidence = WebsiteEvidence(
        start_url=target_url,
        normalized_start_url=target_url,
        robots=robots,
        pages=pages,
        pages_crawled=len(pages),
        pages_discovered=len(pages),
    )
    manager = ExtractionManager()
    extraction = manager.extract(web_evidence)
    return extraction, web_evidence


def test_blog_html_with_no_jsonld_has_no_sd_defect_in_adobe_output():
    """Blog or general page with no JSON-LD markup should NOT emit defects in Adobe report."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Engineering Blog - AI Technology Trends</title>
        <meta name="description" content="Read about the latest AI research and developments." />
    </head>
    <body>
        <header><nav><a href="/">Home</a><a href="/articles">Articles</a></nav></header>
        <main>
            <h1>Engineering Insights on AI Architecture</h1>
            <p>Welcome to our tech blog where we discuss deep learning systems, agentic workflows, and web discovery.</p>
        </main>
        <footer><p>© 2026 Engineering Blog</p></footer>
    </body>
    </html>
    """
    extraction, website = create_mock_extraction_result([
        {
            "url": "https://example.com/blog/ai-trends",
            "title": "Engineering Blog - AI Technology Trends",
            "headings": [{"level": "h1", "text": "Engineering Insights on AI Architecture"}],
            "paragraphs": ["Welcome to our tech blog where we discuss deep learning systems, agentic workflows, and web discovery."],
            "meta_tags": [{"name": "description", "content": "Read about the latest AI research and developments."}],
            "raw_html": html,
            "rendered_html": html,
            "jsonld_raw_blocks": [],
        }
    ])

    findings = run_structured_data_audit(extraction, website)
    # Filter for defects (FAIL or WARNING)
    defects = [f for f in findings if f.status in (FindingStatus.FAIL, FindingStatus.WARNING)]
    assert len(defects) == 0, f"Expected 0 SD defects on blog page without schema, got: {defects}"

    # Verify that Adobe report drops non-defects and has 0 SD findings
    report = AdobeReportComposer.compose("https://example.com", findings)
    assert report["summary"]["total_findings"] == 0
    assert len(report["findings"]) == 0


def test_product_html_missing_offer_fields_may_flag():
    """Product page with incomplete Schema.org Product/Offer markup may legitimately flag."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pro Gaming Mouse - Buy Now</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Pro Gaming Mouse"
        }
        </script>
    </head>
    <body>
        <h1>Pro Gaming Mouse</h1>
        <div class="product-info">
            <span class="price">$79.99</span>
            <button class="buy-btn">Add to Cart</button>
        </div>
    </body>
    </html>
    """
    findings = audit_structured_data(html, "https://example.com/products/gaming-mouse")
    sd004 = next((f for f in findings if f.check_id == "SD-004"), None)
    assert sd004 is not None
    assert sd004.status in (FindingStatus.WARNING, FindingStatus.INFO, FindingStatus.FAIL)


def test_js_shell_low_word_count_no_eg01_high():
    """JS-shell homepage with minimal pre-rendered words (<80) must NOT emit EG-01 HIGH."""
    extraction, website = create_mock_extraction_result([
        {
            "url": "https://example.com",
            "title": "App Shell",
            "headings": [],
            "paragraphs": ["Loading application..."],
            "visible_text": "Loading application...",
            "links": [],
        }
    ])

    findings = run_engagement_audit(extraction, website)
    eg01 = next((f for f in findings if f.check_id == "EG-01"), None)
    # Should either be NOT_APPLICABLE or not HIGH severity
    if eg01:
        assert eg01.status == FindingStatus.NOT_APPLICABLE or eg01.severity != FindingSeverity.HIGH


def test_footer_copyright_only_no_fc02_staleness():
    """Footer copyright year (e.g. '© 2024') must NOT trigger FC-02 content staleness."""
    extraction, website = create_mock_extraction_result([
        {
            "url": "https://example.com",
            "title": "Living Brand Homepage",
            "headings": [{"level": "h1", "text": "Next-Gen Cloud Solutions"}],
            "paragraphs": [
                "Enterprise cloud scaling, telemetry, and automated deployment.",
                "© 2024 Cloud Solutions Inc. All rights reserved."
            ],
            "meta_tags": [],
            "jsonld_raw_blocks": [],
        }
    ])

    findings = run_freshness_corroboration(extraction, website)
    fc02 = next((f for f in findings if f.check_id == "FC-02"), None)
    # FC-02 should be NOT_APPLICABLE or PASS since no machine-readable date metadata exists
    if fc02:
        assert fc02.status in (FindingStatus.NOT_APPLICABLE, FindingStatus.PASS, FindingStatus.INFO)


def test_forbidden_checks_never_in_report():
    """Adobe report output must never flag missing /llms.txt, OpenAPI, or chat widget."""
    extraction, website = create_mock_extraction_result([
        {
            "url": "https://example.com",
            "title": "Company Home",
            "headings": [{"level": "h1", "text": "Welcome to Company"}],
            "paragraphs": ["We provide professional consulting services across industries."],
            "links": [{"href": "https://example.com/services", "text": "Services"}],
        }
    ])

    findings = run_engagement_audit(extraction, website)
    for f in findings:
        text = (f.title + " " + (f.description or "")).lower()
        assert "llms.txt" not in text
        assert "openapi" not in text
        assert "chatbot" not in text


def test_suggested_action_priority_in_high_medium_low():
    """All composed findings in the Adobe report must have priority in {'high', 'medium', 'low'}."""
    ev = Evidence(
        location="https://example.com",
        source_url="https://example.com",
        evidence_type="test",
        observed={"info": "sample"},
        expected={"info": "expected"}
    )
    mock_findings = [
        Finding(
            skill="crawl-render-audit",
            check_id="CR-001",
            title="Broken Link",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.CRITICAL,
            description="Critical 500 error",
            evidence=[ev],
            recommendation="Fix server response",
        ),
        Finding(
            skill="engagement-audit",
            check_id="EG-01",
            title="Missing H1",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description="High defect",
            evidence=[ev],
            recommendation="Add primary heading",
        ),
        Finding(
            skill="entity-identity-audit",
            check_id="EI-02",
            title="Social Link Broken",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description="Medium defect",
            evidence=[ev],
            recommendation="Update social profile link",
        ),
        Finding(
            skill="crawl-render-audit",
            check_id="CR-006",
            title="Meta Description Missing",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description="Low defect",
            evidence=[ev],
            recommendation="Add meta description",
        ),
    ]

    report = AdobeReportComposer.compose("https://example.com", mock_findings)
    assert report["summary"]["total_findings"] == 4
    for f in report["findings"]:
        priority = f["suggested_action"]["priority"]
        assert priority in {"high", "medium", "low"}, f"Unexpected priority {priority}"
