"""Unit and Integration tests for all Step 3 Analysis Skills and Adobe Report Composer."""

import json
import pytest
from typing import List

from src.evidence.models import WebsiteEvidence, PageEvidence, RobotsEvidence, LinkEvidence
from src.extraction.extraction_manager import ExtractionManager
from src.shared.evidence_schema import ExtractionResult, CanonicalEvidence
from src.models import Finding, FindingSeverity, FindingStatus, Evidence
from src.analysis.fact_quality_audit import run_fact_quality_audit
from src.analysis.freshness_corroboration import run_freshness_corroboration
from src.analysis.entity_identity_audit import run_entity_identity_audit
from src.analysis.engagement_audit import run_engagement_audit
from src.analysis.structured_data_audit import run_structured_data_audit
from src.analysis.crawl_render_audit import run_crawl_render_audit
from src.reporting.composer import AdobeReportComposer


# ==============================================================================
# Helper fixtures / builders
# ==============================================================================

def create_mock_extraction_result(pages_data: List[dict], target_url: str = "https://example.com") -> ExtractionResult:
    """Create a populated ExtractionResult and WebsiteEvidence using ExtractionManager."""
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
    return manager.extract(web_evidence)


# ==============================================================================
# Fact Quality Audit Tests
# ==============================================================================

def test_fact_quality_fq02_contradictory_prices():
    """Verify FQ-02 detects contradictory pricing across pages."""
    pages_data = [
        {
            "url": "https://example.com/pricing",
            "title": "Pricing Plans",
            "paragraphs": ["Our Pro Plan is $49 per month billed annually."],
        },
        {
            "url": "https://example.com/features",
            "title": "Features & Plans",
            "paragraphs": ["Get the Pro Plan for only $99 per month."],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_fact_quality_audit(ext_res)

    fq02 = [f for f in findings if f.check_id == "FQ-02"]
    assert len(fq02) >= 1
    assert fq02[0].status == FindingStatus.FAIL
    assert fq02[0].severity == FindingSeverity.HIGH
    assert len(fq02[0].evidence) >= 2


def test_fact_quality_fq03_unitless_numbers():
    """Verify FQ-03 detects standalone large numbers without qualifying units."""
    pages_data = [
        {
            "url": "https://example.com/about",
            "title": "About Us",
            "paragraphs": ["We have served over 50,000 across our network."],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_fact_quality_audit(ext_res)

    fq03 = [f for f in findings if f.check_id == "FQ-03"]
    assert len(fq03) >= 1
    assert fq03[0].status == FindingStatus.WARNING
    assert "50,000" in fq03[0].description


def test_fact_quality_fq04_ungrounded_superlatives():
    """Verify FQ-04 detects marketing superlatives without third-party citations."""
    pages_data = [
        {
            "url": "https://example.com/",
            "title": "Homepage",
            "paragraphs": ["We are the #1 industry-leading platform for enterprise growth."],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_fact_quality_audit(ext_res)

    fq04 = [f for f in findings if f.check_id == "FQ-04"]
    assert len(fq04) >= 1
    assert fq04[0].status == FindingStatus.WARNING
    assert fq04[0].severity == FindingSeverity.MEDIUM


# ==============================================================================
# Freshness Corroboration Tests
# ==============================================================================

def test_freshness_fc01_date_disagreement():
    """Verify FC-01 flags disagreement between visible text date and schema dateModified."""
    json_ld_str = '{"@context": "https://schema.org", "@type": "Article", "dateModified": "2026-01-15"}'
    pages_data = [
        {
            "url": "https://example.com/blog/ai-trends",
            "title": "AI Trends",
            "paragraphs": ["Last updated on March 20, 2024 by our research team."],
            "jsonld_raw_blocks": [json_ld_str],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_freshness_corroboration(ext_res)

    fc01 = [f for f in findings if f.check_id == "FC-01"]
    assert len(fc01) >= 1
    assert fc01[0].status == FindingStatus.WARNING


def test_freshness_fc02_staleness_and_footer_copyright_ignored():
    """Verify FC-02 detects content staleness >12 months while ignoring footer copyright year."""
    json_ld_str = '{"@context": "https://schema.org", "@type": "Article", "dateModified": "2022-05-10T10:00:00Z"}'
    pages_data = [
        {
            "url": "https://example.com/docs/guide",
            "title": "Integration Guide",
            "paragraphs": [
                "This guide walks through setup.",
                "Copyright © 2026 Example Corp. All rights reserved."
            ],
            "jsonld_raw_blocks": [json_ld_str],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_freshness_corroboration(ext_res)

    fc02 = [f for f in findings if f.check_id == "FC-02"]
    assert len(fc02) >= 1
    assert fc02[0].status == FindingStatus.WARNING
    assert "2022" in fc02[0].description


def test_freshness_fc03_offline_public_corroboration_resilience():
    """Verify FC-03 gracefully handles offline / unreachable corroboration endpoints."""
    ext_res = create_mock_extraction_result([
        {"url": "https://example.com", "title": "Example", "paragraphs": ["Content"]}
    ])
    # Should not raise exception
    findings = run_freshness_corroboration(ext_res)
    fc03 = [f for f in findings if f.check_id == "FC-03"]
    assert len(fc03) >= 1
    assert fc03[0].status in (FindingStatus.PASS, FindingStatus.WARNING, FindingStatus.NOT_APPLICABLE)


# ==============================================================================
# Entity Identity Audit Tests
# ==============================================================================

def test_entity_identity_ei01_brand_name_conflicts():
    """Verify EI-01 flags mismatch between brand name in title and Schema Organization."""
    json_ld_str = '{"@context": "https://schema.org", "@type": "Organization", "name": "Alpha Technologies Inc"}'
    pages_data = [
        {
            "url": "https://example.com/",
            "title": "Welcome to Zeta Cloud Solutions",
            "jsonld_raw_blocks": [json_ld_str],
            "paragraphs": ["Zeta Cloud Solutions offers enterprise data infrastructure."],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_entity_identity_audit(ext_res)

    ei01 = [f for f in findings if f.check_id == "EI-01"]
    assert len(ei01) >= 1
    assert ei01[0].status in (FindingStatus.WARNING, FindingStatus.FAIL)
    assert ei01[0].severity == FindingSeverity.HIGH


def test_entity_identity_ei02_sameas_validation():
    """Verify EI-02 flags malformed or unrecognized sameAs social URLs."""
    json_ld_str = '{"@context": "https://schema.org", "@type": "Organization", "name": "Acme", "sameAs": ["ftp://invalid-social-link", "https://twitter.com/acme"]}'
    pages_data = [
        {
            "url": "https://example.com/",
            "title": "Acme Homepage",
            "jsonld_raw_blocks": [json_ld_str],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_entity_identity_audit(ext_res)

    ei02 = [f for f in findings if f.check_id == "EI-02"]
    assert len(ei02) >= 1
    assert any("ftp://invalid-social-link" in f.description for f in ei02)


def test_entity_identity_ei03_cross_page_nap_phone_conflict():
    """Verify EI-03 flags conflicting phone numbers across pages."""
    pages_data = [
        {
            "url": "https://example.com/contact-us",
            "title": "Contact Us",
            "paragraphs": ["Call our support line: +1 (800) 555-0199 for instant assistance."],
        },
        {
            "url": "https://example.com/support",
            "title": "Support Center",
            "paragraphs": ["Call our direct line: +1 (800) 555-9988 anytime."],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_entity_identity_audit(ext_res)

    ei03 = [f for f in findings if f.check_id == "EI-03"]
    assert len(ei03) >= 1
    assert ei03[0].status in (FindingStatus.FAIL, FindingStatus.WARNING)
    assert len(ei03[0].evidence) >= 2


# ==============================================================================
# Engagement Audit Tests
# ==============================================================================

def test_engagement_eg01_missing_h1_and_cta():
    """Verify EG-01 flags landing page with no H1 or CTA."""
    pages_data = [
        {
            "url": "https://example.com/",
            "title": "Empty Welcome Page",
            "headings": [],  # Missing H1
            "paragraphs": ["A short note without call to action."],
            "links": [{"href": "/privacy", "text": "Privacy"}]
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_engagement_audit(ext_res)

    eg01 = [f for f in findings if f.check_id == "EG-01"]
    assert len(eg01) >= 1
    assert eg01[0].status == FindingStatus.FAIL


def test_engagement_eg03_interior_page_lacking_breadcrumbs():
    """Verify EG-03 flags deep interior page lacking breadcrumbs."""
    pages_data = [
        {
            "url": "https://example.com/products/software/analytics/v2",
            "title": "Analytics V2 Details",
            "headings": [{"level": "h1", "text": "Analytics V2"}],
            "paragraphs": ["Deep page details."],
            "links": [{"href": "/home", "text": "Home"}],
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_engagement_audit(ext_res)

    eg03 = [f for f in findings if f.check_id == "EG-03"]
    assert len(eg03) >= 1
    assert eg03[0].status == FindingStatus.WARNING


def test_engagement_eg04_learn_more_loop():
    """Verify EG-04 flags circular self-referencing Learn More link."""
    pages_data = [
        {
            "url": "https://example.com/solutions",
            "title": "Enterprise Solutions",
            "headings": [{"level": "h1", "text": "Solutions"}],
            "paragraphs": ["Discover our enterprise offerings."],
            "links": [
                {"href": "https://example.com/solutions", "text": "Learn More"},
                {"href": "#", "text": "Read More"}
            ]
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_engagement_audit(ext_res)

    eg04 = [f for f in findings if f.check_id == "EG-04"]
    assert len(eg04) >= 1
    assert eg04[0].status == FindingStatus.WARNING


def test_engagement_forbidden_checks_not_emitted():
    """Verify engagement-audit does NOT flag missing machine files (/llms.txt, /openapi.json)."""
    pages_data = [
        {
            "url": "https://example.com/",
            "title": "Welcome",
            "headings": [{"level": "h1", "text": "Welcome to AI Ready"}],
            "paragraphs": ["Get started today with our services."],
            "links": [{"href": "/signup", "text": "Get Started"}]
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_engagement_audit(ext_res)

    check_ids = [f.check_id for f in findings]
    assert "LLMS-TXT" not in check_ids
    assert "OPENAPI" not in check_ids
    assert not any("llms.txt" in (f.description or "").lower() for f in findings)


# ==============================================================================
# Structured Data Guardrail Tests
# ==============================================================================

def test_structured_data_missing_schema_on_non_product_is_not_defect():
    """Verify structured_data_audit does not emit high/critical defect for missing schema on general page."""
    pages_data = [
        {
            "url": "https://example.com/blog/first-post",
            "title": "My Blog Post",
            "headings": [{"level": "h1", "text": "First Post"}],
            "paragraphs": ["This is a blog post without json-ld schema."],
            "jsonld_raw_blocks": []
        }
    ]
    ext_res = create_mock_extraction_result(pages_data)
    findings = run_structured_data_audit(ext_res)

    critical_or_high = [f for f in findings if f.status == FindingStatus.FAIL and f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)]
    assert len(critical_or_high) == 0


# ==============================================================================
# Adobe Report Composer Tests
# ==============================================================================

def test_adobe_report_composer_schema_and_formatting():
    """Verify AdobeReportComposer outputs the exact required JSON schema and strips PASS/INFO."""
    ev1 = Evidence(source_url="https://example.com/p1", evidence_type="dom", observed="Contradicting price $49")
    ev2 = Evidence(source_url="https://example.com/p2", evidence_type="dom", observed="Contradicting price $99")

    findings = [
        # Pass item -> should be omitted from public report
        Finding(
            skill="crawl-render-audit",
            check_id="CR-01",
            title="Sitemap Available",
            status=FindingStatus.PASS,
            severity=FindingSeverity.INFO,
            description="Sitemap found.",
            evidence=[ev1],
            recommendation="Keep updated."
        ),
        # Info item -> should be omitted
        Finding(
            skill="crawl-render-audit",
            check_id="CR-02",
            title="Robots txt note",
            status=FindingStatus.NOT_APPLICABLE,
            severity=FindingSeverity.INFO,
            description="Info note.",
            evidence=[ev1],
            recommendation="None."
        ),
        # High failure -> should be included
        Finding(
            skill="fact-quality-audit",
            check_id="FQ-02",
            title="Contradictory Pricing",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description="Pro plan priced at $49 and $99 across pages.",
            evidence=[ev1, ev2],
            recommendation="Unify pricing across website."
        ),
        # Critical failure -> should be sorted first
        Finding(
            skill="entity-identity-audit",
            check_id="EI-01",
            title="Brand Identity Conflict",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.CRITICAL,
            description="Brand name contradicts schema entity.",
            evidence=[ev1],
            recommendation="Update Organization schema name."
        ),
        # Item with empty evidence -> should be omitted
        Finding(
            skill="engagement-audit",
            check_id="EG-01",
            title="No Evidence Bug",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.MEDIUM,
            description="Defect without evidence.",
            evidence=[],
            recommendation="Add evidence."
        )
    ]

    composer = AdobeReportComposer()
    report_dict = composer.compose(target_url="https://example.com", findings=findings)

    # 1. Root structure verification
    assert "site" in report_dict
    assert report_dict["site"] in ("example.com", "https://example.com")
    assert "audited_at" in report_dict
    assert "summary" in report_dict
    assert "findings" in report_dict

    # 2. Summary counts verification
    summary = report_dict["summary"]
    assert summary["total_findings"] == 2
    assert summary["critical"] == 1
    assert summary["high"] == 1
    assert summary["medium"] == 0
    assert summary["low"] == 0

    # 3. Findings list verification
    public_findings = report_dict["findings"]
    assert len(public_findings) == 2

    # First should be Critical (EI-01), second High (FQ-02)
    f1 = public_findings[0]
    assert f1["id"] == "F-001"
    assert f1["severity"] == "critical"
    assert f1["title"] == "Brand Identity Conflict"
    assert isinstance(f1["suggested_action"], dict)
    assert f1["suggested_action"]["priority"] == "P1"
    assert isinstance(f1["evidence"], str) and len(f1["evidence"]) > 0

    f2 = public_findings[1]
    assert f2["id"] == "F-002"
    assert f2["severity"] == "high"
    assert f2["title"] == "Contradictory Pricing"
    assert f2["suggested_action"]["priority"] == "P2"
    assert isinstance(f2["evidence"], str) and len(f2["evidence"]) > 0

    # Verify JSON serializability
    json_str = json.dumps(report_dict)
    assert "F-001" in json_str
    assert "F-002" in json_str
