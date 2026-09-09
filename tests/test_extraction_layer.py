"""Comprehensive Unit and Integration Tests for Step 2 Evidence Collection / Extraction Layer."""

import json
import os
from typing import Any, Dict, List
import pytest

from src.evidence.models import (
    ContactEvidence,
    DateEvidence,
    DocumentEvidence,
    FormEvidence,
    FormInputField,
    ImageEvidence,
    LinkEvidence,
    PageEvidence,
    Provenance,
    RobotsEvidence,
    SitemapEntry,
    SitemapEvidence,
    UserAgentRuleGroup,
    WebsiteEvidence,
)
from src.extraction.entity_extractor import EntityExtractor
from src.extraction.extraction_manager import ExtractionManager
from src.extraction.freshness_extractor import FreshnessExtractor, try_normalize_date
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
)


@pytest.fixture
def sample_crawler_json() -> Dict[str, Any]:
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "crawler_response.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================================
# 1. EVIDENCE ID GENERATOR TESTS
# =========================================================================

def test_id_generator_sequential_and_deterministic():
    gen = EvidenceIdGenerator(prefix="EV-", digits=5, start=1)
    ids = [gen.next_id() for _ in range(5)]
    assert ids == ["EV-00001", "EV-00002", "EV-00003", "EV-00004", "EV-00005"]

    gen.reset()
    assert gen.next_id() == "EV-00001"


# =========================================================================
# 2. HTTP EXTRACTOR TESTS
# =========================================================================

def test_http_extractor_normal_and_headers():
    extractor = HTTPExtractor()
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "X-Robots-Tag": "noindex, nofollow",
        "Last-Modified": "Sun, 15 Feb 2026 12:00:00 GMT",
        "Cache-Control": "max-age=3600",
        "ETag": '"abc123etag"',
    }
    evidence = extractor.extract_http_evidence(
        requested_url="https://example.com/page",
        final_url="https://example.com/page",
        status_code=200,
        headers=headers,
        response_time_ms=120.5,
    )

    types = [e.type for e in evidence]
    assert EvidenceType.HTTP_STATUS in types
    assert EvidenceType.RAW_HEADERS in types
    assert EvidenceType.HTTP_HEADER in types
    assert EvidenceType.RESPONSE_TIMING in types

    status_ev = next(e for e in evidence if e.type == EvidenceType.HTTP_STATUS)
    assert status_ev.data["status_code"] == 200
    assert status_ev.data["is_success"] is True

    # Check X-Robots-Tag normalization without evaluation
    xrobots_ev = next(e for e in evidence if e.type == EvidenceType.HTTP_HEADER and e.data["name"] == "x-robots-tag")
    assert xrobots_ev.data["value"] == "noindex, nofollow"
    assert xrobots_ev.provenance.location == "header:x-robots-tag"


def test_http_extractor_redirect_chain():
    extractor = HTTPExtractor()
    redirects = [
        {"from_url": "http://example.com", "to_url": "https://example.com", "status_code": 301},
        {"from_url": "https://example.com", "to_url": "https://example.com/home", "status_code": 302},
    ]
    evidence = extractor.extract_http_evidence(
        requested_url="http://example.com",
        final_url="https://example.com/home",
        status_code=200,
        redirect_chain=redirects,
    )

    redir_evs = [e for e in evidence if e.type == EvidenceType.HTTP_REDIRECT]
    assert len(redir_evs) == 2
    assert redir_evs[0].data["from_url"] == "http://example.com"
    assert redir_evs[1].data["to_url"] == "https://example.com/home"


def test_http_extractor_missing_headers():
    extractor = HTTPExtractor()
    evidence = extractor.extract_http_evidence(
        requested_url="https://example.com/empty-headers",
        status_code=404,
        headers=None,
    )
    assert len(evidence) >= 1
    status_ev = evidence[0]
    assert status_ev.data["status_code"] == 404
    assert status_ev.data["is_client_error"] is True


# =========================================================================
# 3. TEXT EXTRACTOR TESTS
# =========================================================================

def test_text_extractor_hierarchy_and_structures():
    extractor = TextExtractor()
    html = """
    <html><body>
        <h1>Main Topic Heading</h1>
        <h2>Sub Topic 1</h2>
        <p>First paragraph introducing the concept.</p>
        <h2>Sub Topic 2</h2>
        <p>Second paragraph with details.</p>
        <ul><li>Item Alpha</li><li>Item Beta</li></ul>
        <table><tr><th>Header 1</th></tr><tr><td>Row 1</td></tr></table>
        <blockquote>Quoted assertion.</blockquote>
        <figure><figcaption>Figure caption info</figcaption></figure>
    </body></html>
    """
    evidence = extractor.extract_text_evidence(url="https://example.com/text", html_content=html)

    types = [e.type for e in evidence]
    assert EvidenceType.HEADING in types
    assert EvidenceType.PARAGRAPH in types
    assert EvidenceType.LIST_BLOCK in types
    assert EvidenceType.TABLE_BLOCK in types
    assert EvidenceType.BLOCKQUOTE_BLOCK in types
    assert EvidenceType.CAPTION_BLOCK in types
    assert EvidenceType.VISIBLE_TEXT_SUMMARY in types
    assert EvidenceType.TEXT_EXTRACTABILITY_SIGNAL in types

    h1_ev = next(e for e in evidence if e.type == EvidenceType.HEADING and e.data["level"] == 1)
    assert h1_ev.data["text"] == "Main Topic Heading"
    assert h1_ev.data["tag"] == "h1"

    list_ev = next(e for e in evidence if e.type == EvidenceType.LIST_BLOCK)
    assert list_ev.data["items"] == ["Item Alpha", "Item Beta"]


def test_text_extractor_malformed_html_and_empty():
    extractor = TextExtractor()
    # Malformed unclosed tags
    evidence = extractor.extract_text_evidence(url="https://example.com/malformed", html_content="<div><h1>Unclosed <b>heading</div>")
    assert any(e.type == EvidenceType.HEADING for e in evidence)

    # Completely empty
    evidence_empty = extractor.extract_text_evidence(url="https://example.com/empty", html_content="")
    assert any(e.type == EvidenceType.VISIBLE_TEXT_SUMMARY for e in evidence_empty)


# =========================================================================
# 4. METADATA EXTRACTOR TESTS
# =========================================================================

def test_metadata_extractor_title_og_twitter_canonical():
    extractor = MetadataExtractor()
    html = """
    <html>
    <head>
        <title>Brand AI Hub</title>
        <meta name="description" content="Meta description for search.">
        <link rel="canonical" href="https://example.com/canonical-page">
        <meta name="robots" content="noindex, follow">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="og:title" content="OpenGraph Title">
        <meta property="og:image" content="https://example.com/og.jpg">
        <meta name="twitter:card" content="summary_large_image">
    </head>
    <body></body>
    </html>
    """
    evidence = extractor.extract_metadata_evidence(url="https://example.com/meta", html_content=html)

    types = [e.type for e in evidence]
    assert EvidenceType.PAGE_METADATA in types
    assert EvidenceType.CANONICAL_URL in types
    assert EvidenceType.VIEWPORT_META in types
    assert EvidenceType.OPENGRAPH_META in types
    assert EvidenceType.TWITTER_META in types
    assert EvidenceType.ROBOTS_RULE in types

    canon_ev = next(e for e in evidence if e.type == EvidenceType.CANONICAL_URL)
    assert canon_ev.data["canonical_url"] == "https://example.com/canonical-page"

    og_ev = next(e for e in evidence if e.type == EvidenceType.OPENGRAPH_META)
    assert og_ev.data["fields"]["og:title"] == "OpenGraph Title"


# =========================================================================
# 5. SCHEMA EXTRACTOR TESTS
# =========================================================================

def test_schema_extractor_jsonld_and_microdata():
    extractor = SchemaExtractor()
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": ["Organization", "Brand"],
            "name": "Acme Brand",
            "url": "https://example.com"
        }
        </script>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "AI Audit Suite"
        }
        </script>
    </head>
    <body>
        <div itemscope itemtype="https://schema.org/LocalBusiness">
            <span itemprop="name">Acme Local</span>
        </div>
    </body>
    </html>
    """
    evidence = extractor.extract_schema_evidence(url="https://example.com/schema", html_content=html)

    types = [e.type for e in evidence]
    assert EvidenceType.JSONLD_RAW in types
    assert EvidenceType.JSONLD_PARSED in types
    assert EvidenceType.SCHEMA_TYPE in types
    assert EvidenceType.MICRODATA_ITEM in types

    raw_blocks = [e for e in evidence if e.type == EvidenceType.JSONLD_RAW]
    assert len(raw_blocks) == 2
    assert raw_blocks[0].is_raw is True

    # Check multi-type detection
    schema_types = [e for e in evidence if e.type == EvidenceType.SCHEMA_TYPE]
    all_types = []
    for st in schema_types:
        all_types.extend(st.data["types"])
    assert "Organization" in all_types
    assert "Brand" in all_types
    assert "Product" in all_types

    # Check microdata
    m_ev = next(e for e in evidence if e.type == EvidenceType.MICRODATA_ITEM)
    assert "LocalBusiness" in m_ev.data["itemtype"]


def test_schema_extractor_malformed_json():
    extractor = SchemaExtractor()
    html = """
    <html><head>
        <script type="application/ld+json">{ "bad": json without quotes </script>
    </head></html>
    """
    evidence = extractor.extract_schema_evidence(url="https://example.com/bad-json", html_content=html)
    assert any(e.type == EvidenceType.JSONLD_RAW for e in evidence)
    assert any("schema_parse_error" in str(e.type) or e.type == "schema_parse_error" for e in evidence)


# =========================================================================
# 6. ROBOTS EXTRACTOR TESTS
# =========================================================================

def test_robots_extractor_ai_bots_and_sitemaps():
    extractor = RobotsExtractor()
    content = """
    User-agent: *
    Disallow: /admin/
    Allow: /public/
    Crawl-delay: 2

    User-agent: GPTBot
    User-agent: ClaudeBot
    User-agent: PerplexityBot
    Disallow: /private/
    Allow: /docs/

    Sitemap: https://example.com/sitemap.xml
    """
    evidence = extractor.extract_robots_evidence(
        raw_robots_content=content,
        robots_url="https://example.com/robots.txt",
        status_code=200,
    )

    types = [e.type for e in evidence]
    assert EvidenceType.RAW_ROBOTS in types
    assert EvidenceType.ROBOTS_RULE in types
    assert EvidenceType.ROBOTS_CRAWL_DELAY in types
    assert EvidenceType.ROBOTS_SITEMAP_DECLARATION in types

    # Check GPTBot specific rules
    gpt_disallows = [
        e for e in evidence
        if e.type == EvidenceType.ROBOTS_RULE
        and e.data["user_agent"] == "GPTBot"
        and e.data["directive"] == "Disallow"
    ]
    assert len(gpt_disallows) == 1
    assert gpt_disallows[0].data["path"] == "/private/"

    sitemap_ev = next(e for e in evidence if e.type == EvidenceType.ROBOTS_SITEMAP_DECLARATION)
    assert sitemap_ev.data["declared_sitemap_url"] == "https://example.com/sitemap.xml"


# =========================================================================
# 7. FRESHNESS EXTRACTOR TESTS
# =========================================================================

def test_freshness_extractor_all_sources():
    extractor = FreshnessExtractor()
    headers = {"Last-Modified": "Sun, 15 Feb 2026 12:00:00 GMT"}
    jsonld_objs = [
        {
            "@type": "Article",
            "datePublished": "2026-01-10T09:00:00Z",
            "dateModified": "2026-02-12",
        }
    ]
    meta_tags = [{"property": "article:modified_time", "content": "2026-02-14"}]
    visible_dates = ["Jan 15, 2026"]
    sitemap_lastmod = "2026-02-16"

    evidence = extractor.extract_freshness_evidence(
        url="https://example.com/freshness",
        headers=headers,
        jsonld_objects=jsonld_objs,
        meta_tags=meta_tags,
        visible_dates=visible_dates,
        sitemap_lastmod=sitemap_lastmod,
    )

    assert len(evidence) >= 5
    kinds = [e.data["kind"] for e in evidence]
    assert "last_modified_header" in kinds
    assert "datePublished" in kinds
    assert "dateModified" in kinds
    assert "article:modified_time" in kinds
    assert "visible_date" in kinds
    assert "sitemap_lastmod" in kinds

    # Verify normalization preserved raw_value
    for e in evidence:
        assert "raw_value" in e.data
        assert "normalized_value" in e.data
        assert e.provenance.url == "https://example.com/freshness"


def test_try_normalize_date():
    assert try_normalize_date("2026-02-15") == "2026-02-15"
    assert try_normalize_date("Feb 15, 2026") == "2026-02-15"
    assert try_normalize_date("Sun, 15 Feb 2026 12:00:00 GMT") == "2026-02-15"
    assert try_normalize_date("invalid-text-date") == "invalid-text-date"


# =========================================================================
# 8. ENTITY EXTRACTOR TESTS
# =========================================================================

def test_entity_extractor_multi_source():
    extractor = EntityExtractor()
    jsonld_objs = [
        {
            "@type": "Organization",
            "name": "Acme Global",
            "logo": "https://example.com/logo.png",
            "telephone": "+1-800-555-0199",
            "email": "corp@example.com",
            "sameAs": [
                "https://twitter.com/Acme",
                "https://www.wikidata.org/wiki/Q99999",
            ],
            "address": {
                "streetAddress": "123 Tech Blvd",
                "addressLocality": "Austin",
                "addressRegion": "TX",
            },
        }
    ]
    contacts = ContactEvidence(
        emails=["support@example.com"],
        phone_numbers=["+1-800-555-0100"],
        addresses=["123 Tech Blvd, Austin, TX"],
    )

    evidence = extractor.extract_entity_evidence(
        url="https://example.com/about",
        jsonld_objects=jsonld_objs,
        contacts=contacts,
    )

    types = [e.type for e in evidence]
    assert EvidenceType.ENTITY_NAME in types
    assert EvidenceType.ENTITY_LOGO in types
    assert EvidenceType.ENTITY_PHONE in types
    assert EvidenceType.ENTITY_EMAIL in types
    assert EvidenceType.SAME_AS_LINK in types
    assert EvidenceType.WIKIDATA_ID in types
    assert EvidenceType.ENTITY_ADDRESS in types

    wiki_ev = next(e for e in evidence if e.type == EvidenceType.WIKIDATA_ID)
    assert wiki_ev.data["wikidata_id"] == "Q99999"


# =========================================================================
# 9. LINK EXTRACTOR TESTS
# =========================================================================

def test_link_extractor_classifications_and_docs():
    extractor = LinkExtractor()
    links = [
        LinkEvidence(
            href="https://example.com/internal-page",
            source_page="https://example.com/",
            anchor_text="Internal Link",
            is_internal=True,
            rel=None,
        ),
        LinkEvidence(
            href="https://external.org/partner",
            source_page="https://example.com/",
            anchor_text="External Partner",
            is_internal=False,
            rel="nofollow sponsored",
        ),
    ]
    docs = [
        DocumentEvidence(
            url="https://example.com/whitepaper.pdf",
            source_page="https://example.com/",
            filename="whitepaper.pdf",
            file_type="pdf",
            anchor_text="Download PDF",
        )
    ]

    evidence = extractor.extract_link_evidence(
        url="https://example.com/",
        links=links,
        documents=docs,
    )

    types = [e.type for e in evidence]
    assert EvidenceType.LINK_ITEM in types
    assert EvidenceType.DOCUMENT_RESOURCE in types

    ext_link_ev = next(e for e in evidence if e.type == EvidenceType.LINK_ITEM and not e.data["is_internal"])
    assert ext_link_ev.data["is_nofollow"] is True
    assert ext_link_ev.data["is_sponsored"] is True

    doc_ev = next(e for e in evidence if e.type == EvidenceType.DOCUMENT_RESOURCE)
    assert doc_ev.data["file_type"] == "pdf"


# =========================================================================
# 10. MEDIA & FORM EXTRACTOR TESTS
# =========================================================================

def test_media_and_form_extractor():
    extractor = MediaExtractor()
    images = [
        ImageEvidence(
            declared_url="/hero.png",
            resolved_url="https://example.com/hero.png",
            url="https://example.com/hero.png",
            source_page="https://example.com/",
            alt="Hero Banner",
            declared_width=1200,
            declared_height=600,
            format="png",
            caption="Hero Diagram",
            is_tracking_or_icon=False,
        ),
        ImageEvidence(
            declared_url="/pixel.gif",
            resolved_url="https://example.com/pixel.gif",
            url="https://example.com/pixel.gif",
            source_page="https://example.com/",
            declared_width=1,
            declared_height=1,
            is_tracking_or_icon=True,
            filter_reason="dimensions_<=_10px",
        ),
    ]
    forms = [
        FormEvidence(
            source_page="https://example.com/",
            action="https://example.com/contact",
            method="post",
            inputs=[
                FormInputField(input_type="email", name="email", placeholder="you@company.com"),
            ],
            buttons=["Submit"],
        )
    ]

    evidence = extractor.extract_media_evidence(
        url="https://example.com/",
        images=images,
        forms=forms,
    )

    types = [e.type for e in evidence]
    assert EvidenceType.IMAGE_ITEM in types
    assert EvidenceType.FORM_ITEM in types

    img_ev = next(e for e in evidence if e.type == EvidenceType.IMAGE_ITEM and not e.data["is_tracking_or_icon"])
    assert img_ev.data["declared_width"] == 1200
    assert img_ev.data["caption"] == "Hero Diagram"

    form_ev = next(e for e in evidence if e.type == EvidenceType.FORM_ITEM)
    assert form_ev.data["method"] == "post"
    assert form_ev.data["inputs_count"] == 1


# =========================================================================
# 11. RESOURCE EXTRACTOR (LLMS.TXT, OPENAPI, SITEMAP) TESTS
# =========================================================================

def test_resource_extractor_llmstxt_openapi_sitemap():
    extractor = ResourceExtractor()

    # llms.txt test
    llms_content = "# Project Title\n> Project Summary\n## Section 1\nSection 1 details."
    llms_evs = extractor.extract_llmstxt_evidence(url="https://example.com/llms.txt", content=llms_content, status_code=200)
    assert any(e.type == EvidenceType.RAW_LLMSTXT for e in llms_evs)
    assert any(e.type == EvidenceType.LLMSTXT_RESOURCE for e in llms_evs)
    llms_parsed = next(e for e in llms_evs if e.type == EvidenceType.LLMSTXT_RESOURCE)
    assert llms_parsed.data["section_count"] >= 2

    # openapi.json test
    openapi_content = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Acme REST API"},
        "paths": {"/api/v1/audits": {}, "/api/v1/health": {}},
    })
    openapi_evs = extractor.extract_openapi_evidence(url="https://example.com/openapi.json", raw_json_content=openapi_content)
    assert any(e.type == EvidenceType.RAW_OPENAPI for e in openapi_evs)
    assert any(e.type == EvidenceType.OPENAPI_RESOURCE for e in openapi_evs)
    openapi_parsed = next(e for e in openapi_evs if e.type == EvidenceType.OPENAPI_RESOURCE)
    assert openapi_parsed.data["paths_count"] == 2


# =========================================================================
# 12. SITE EXTRACTOR TESTS
# =========================================================================

def test_site_extractor():
    extractor = SiteExtractor()
    evidence = extractor.extract_site_evidence(
        start_url="https://example.com/",
        pages_discovered=10,
        pages_crawled=5,
        max_depth=3,
        truncated=True,
        truncation_reason="max_pages_limit_reached (5/5)",
        resource_summary={"html_pages": 5, "images": 12},
        failed_urls=[{"url": "https://example.com/broken", "status_code": 404, "error": "Not Found"}],
        skipped_urls=[{"url": "https://example.com/admin", "reason": "robots_disallowed"}],
    )

    types = [e.type for e in evidence]
    assert EvidenceType.CRAWL_COVERAGE in types
    assert EvidenceType.CRAWL_RESOURCE_SUMMARY in types
    assert EvidenceType.FAILED_URL_RECORD in types
    assert EvidenceType.SKIPPED_URL_RECORD in types

    cov_ev = next(e for e in evidence if e.type == EvidenceType.CRAWL_COVERAGE)
    assert cov_ev.data["truncated"] is True
    assert "max_pages_limit_reached" in cov_ev.data["truncation_reason"]


# =========================================================================
# 13. EXTRACTION MANAGER INTEGRATION & TRACEABILITY TESTS
# =========================================================================

def test_extraction_manager_full_fixture_run(sample_crawler_json):
    """Verifies that ExtractionManager processes a full crawler fixture cleanly and deterministically."""
    manager = ExtractionManager()
    result = manager.extract(sample_crawler_json)

    assert isinstance(result, ExtractionResult)
    assert len(result.errors) == 0
    assert len(result.evidence) > 20
    assert result.metadata["total_evidence_count"] == len(result.evidence)

    # 1. Check Unique Sequential IDs
    ids = [e.id for e in result.evidence]
    assert len(ids) == len(set(ids))
    assert ids[0] == "EV-00001"
    assert ids[-1] == f"EV-{str(len(ids)).zfill(5)}"

    # 2. Check Traceability & Provenance
    for ev in result.evidence:
        assert isinstance(ev, CanonicalEvidence)
        assert ev.id.startswith("EV-")
        assert ev.provenance is not None
        assert ev.provenance.source != ""
        assert ev.provenance.extraction_method != ""
        assert ev.timestamp != ""
        assert isinstance(ev.data, dict)

    # 3. Check that Raw Artifacts are preserved
    raw_evs = [e for e in result.evidence if e.is_raw]
    assert len(raw_evs) >= 2  # raw_robots, raw_html, etc.

    # 4. Strictly Verify NO Audit Findings / Scores exist in result
    dumped_str = result.model_dump_json()
    assert "findings" not in result.model_dump()
    assert "overall_score" not in dumped_str
    assert "recommendation" not in dumped_str
    assert "FindingSeverity" not in dumped_str


def test_extraction_manager_deterministic_ordering(sample_crawler_json):
    """Verifies that two consecutive runs produce identical evidence order and IDs."""
    manager1 = ExtractionManager()
    result1 = manager1.extract(sample_crawler_json)

    manager2 = ExtractionManager()
    result2 = manager2.extract(sample_crawler_json)

    assert len(result1.evidence) == len(result2.evidence)
    for ev1, ev2 in zip(result1.evidence, result2.evidence):
        assert ev1.id == ev2.id
        assert ev1.type == ev2.type
        assert ev1.url == ev2.url
        assert ev1.data == ev2.data


def test_extraction_manager_error_resilience():
    """Verifies that a failing extractor records an ExtractionError and does not crash the extraction run."""
    manager = ExtractionManager()

    # Create dummy page with unparseable data
    bad_page = PageEvidence(
        url="https://example.com/bad",
        status_code=200,
        title="Bad Page",
    )

    # Monkeypatch a failing extractor
    def broken_extract(*args, **kwargs):
        raise RuntimeError("Simulated extractor crash")

    manager.http_extractor.extract_http_evidence = broken_extract

    result = manager.extract({"start_url": "https://example.com/", "pages": [bad_page]})
    assert len(result.errors) == 1
    assert result.errors[0].extractor == "http-extractor"
    assert "Simulated extractor crash" in result.errors[0].error
    # Other evidence should still be collected
    assert len(result.evidence) > 0
