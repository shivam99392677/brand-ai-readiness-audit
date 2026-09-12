"""Unit and integration tests for selective Playwright browser rendering layer."""

import pytest
from unittest.mock import MagicMock, patch
from src.crawler.browser import BrowserRenderer, RenderedPageResult
from src.crawler.render_decision import should_render_page, RenderDecision
from src.crawler.engine import SiteCrawler, CrawlConfig
from src.evidence.models import PageEvidence, LinkEvidence, ImageEvidence, Provenance


def test_render_decision_static_page_bypass():
    """Static pages with rich text content must not trigger browser rendering."""
    html = "<html><body><h1>Title</h1><p>" + ("Word " * 100) + "</p><a href='/about'>About</a></body></html>"
    decision = should_render_page(url="https://example.com", http_status=200, html_content=html)
    assert not decision.should_render
    assert len(decision.reasons) == 0


def test_render_decision_spa_shell_container_trigger():
    """Presence of empty framework app shell containers triggers browser rendering."""
    html = "<html><body><div id=\"__next\"></div></body></html>"
    decision = should_render_page(url="https://example.com", http_status=200, html_content=html)
    assert decision.should_render
    assert "Empty app container: #__next" in decision.reasons


def test_render_decision_script_to_text_ratio_trigger():
    """High script-to-text ratio triggers rendering."""
    script = "<script>" + ("console.log(1);" * 500) + "</script>"
    html = f"<html><body>{script}<h1>Hi</h1></body></html>"
    decision = should_render_page(url="https://example.com", http_status=200, html_content=html)
    assert decision.should_render
    assert any("High script-to-text ratio" in r for r in decision.reasons)


def test_browser_renderer_failure_graceful_handling():
    """Browser failures must return a clean failed RenderedPageResult without raising exceptions."""
    renderer = BrowserRenderer(browser_type="chromium", timeout_seconds=1.0)
    with patch.object(renderer, '_render', side_effect=Exception("Navigation timeout of 1000ms exceeded")):
        res = renderer.render_page("https://example.com/timeout")
        assert not res.rendered
        assert res.error is not None
        assert "Navigation timeout" in res.error


def test_browser_renderer_evaluation_free():
    """Browser evidence and metadata must be strictly evaluation-free (no PASS/FAIL/WARNING/score)."""
    res = RenderedPageResult(
        url="https://example.com",
        rendered=True,
        rendered_html="<html><body><h1>SPA Header</h1></body></html>",
        render_time_ms=150.0,
        final_url="https://example.com/",
        reasons=["Empty app container: #root"]
    )
    res_dict = res.to_dict()
    forbidden_terms = ["pass", "fail", "warning", "score", "recommendation"]
    for key in res_dict:
        assert key.lower() not in forbidden_terms


def test_crawler_http_first_selective_rendering_flow():
    """Verify SiteCrawler runs HTTP first, selectively renders when triggered, and preserves discovery provenance."""
    def mock_fetcher(url):
        clean_u = url.rstrip('/')
        if clean_u == "https://example.com":
            # SPA shell
            return 200, "<html><body><div id='root'></div></body></html>", {"content-type": "text/html"}
        elif clean_u == "https://example.com/rendered-link":
            # Static page
            return 200, "<html><body><h1>Rendered Subpage</h1><p>" + ("Content " * 60) + "</p></body></html>", {"content-type": "text/html"}
        return 404, "Not Found", {}

    config = CrawlConfig(
        max_pages=5,
        browser_enabled=True,
        respect_robots=False,
        discover_sitemap=False,
        max_rendered_pages=2,
    )
    crawler = SiteCrawler(config=config)

    # Mock renderer to return rendered DOM containing a browser-discovered link
    rendered_dom = "<html><body><main><h1>Loaded App</h1><a href='/rendered-link'>Dynamic Link</a></main></body></html>"
    mock_render_result = RenderedPageResult(
        url="https://example.com",
        rendered=True,
        rendered_html=rendered_dom,
        render_time_ms=200.0,
        final_url="https://example.com/",
        reasons=["Empty app container: #root"],
    )

    with patch.object(crawler.browser_renderer, 'render_page', return_value=mock_render_result):
        manifest = crawler.crawl_site("https://example.com", custom_fetcher=mock_fetcher)

        assert manifest.pages_crawled >= 1
        assert manifest.pages_rendered == 1
        root_page = next((p for p in manifest.pages if p.url.rstrip('/') == "https://example.com"), None)
        assert root_page is not None
        assert root_page.render_metadata is not None
        assert root_page.render_metadata.rendered is True
        assert root_page.http_evidence is not None
        assert root_page.rendered_evidence is not None

        # Verify browser-discovered link has discovery_method = 'browser_rendered_link'
        browser_link = next((l for l in root_page.links if l.href == "https://example.com/rendered-link"), None)
        assert browser_link is not None
        assert "browser" in browser_link.source_types


def test_browser_failure_does_not_destroy_http_evidence():
    """When browser rendering fails, existing HTTP evidence remains fully preserved."""
    def mock_fetcher(url):
        return 200, "<html><body><div id='root'></div><p>HTTP text</p></body></html>", {"content-type": "text/html"}

    config = CrawlConfig(
        max_pages=1,
        browser_enabled=True,
        respect_robots=False,
        discover_sitemap=False,
    )
    crawler = SiteCrawler(config=config)

    failed_render_result = RenderedPageResult(
        url="https://example.com",
        rendered=False,
        error="Browser crash simulated",
        reasons=["Empty app container: #root"],
    )

    with patch.object(crawler.browser_renderer, 'render_page', return_value=failed_render_result):
        manifest = crawler.crawl_site("https://example.com", custom_fetcher=mock_fetcher)
        assert len(manifest.pages) == 1
        page = manifest.pages[0]
        assert page.http_evidence is not None
        assert page.word_count > 0  # HTTP evidence text preserved
        assert page.render_metadata is not None
        assert page.render_metadata.rendered is False
        assert page.render_metadata.error == "Browser crash simulated"


def test_spa_client_side_rendering_discovery_flow():
    """End-to-end test on local HTTP server simulating a client-rendered SPA."""
    import http.server
    import socketserver
    import threading
    import time

    PORT = 8999

    class LocalSPAHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if "/dynamic-page" in self.path:
                self.wfile.write(b"<html><body><h1>Dynamic Subpage</h1><p>Content loaded on subpage.</p></body></html>")
            else:
                html = """<!DOCTYPE html>
                <html>
                <head><title>SPA Home</title></head>
                <body>
                    <div id="app"></div>
                    <script>
                        document.getElementById('app').innerHTML = '<h1>Rendered App Header</h1><p>Client side rendered paragraph text.</p><a href="/dynamic-page">Dynamic Page Link</a>';
                    </script>
                </body>
                </html>"""
                self.wfile.write(html.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", PORT), LocalSPAHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    time.sleep(0.3)

    try:
        start_url = f"http://127.0.0.1:{PORT}/"
        config = CrawlConfig(
            max_pages=3,
            max_depth=2,
            browser_enabled=True,
            max_rendered_pages=2,
            respect_robots=False,
            discover_sitemap=False,
        )
        crawler = SiteCrawler(config=config)
        manifest = crawler.crawl_site(start_url)

        assert manifest.pages_crawled >= 1
        assert manifest.pages_rendered >= 1
        root_page = next(p for p in manifest.pages if p.url.rstrip('/') == start_url.rstrip('/'))

        assert root_page.http_evidence["word_count"] < 5
        assert root_page.rendered_evidence["word_count"] > 10
        assert len(root_page.http_evidence["links"]) == 0
        assert len(root_page.rendered_evidence["links"]) == 1

        discovered_dyn_link = next(
            (d for d in manifest.website_evidence.discovered_urls if d.discovery_method == "browser_rendered_link"),
            None
        )
        assert discovered_dyn_link is not None
        assert "dynamic-page" in discovered_dyn_link.url
    finally:
        server.shutdown()
        server.server_close()

