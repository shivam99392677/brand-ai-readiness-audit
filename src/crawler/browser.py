"""Isolated Browser Renderer abstraction using Playwright Chromium.

Executes passive client-side rendering for JavaScript web pages without interacting
with forms, login buttons, purchases, or credentials.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class RenderedPageResult(BaseModel):
    """Objective result of a browser page rendering operation."""
    url: str = Field(..., description="Target URL")
    final_url: Optional[str] = Field(default=None, description="Final URL after JavaScript redirects")
    status_code: int = Field(default=200, description="HTTP status code if captured")
    html: Optional[str] = Field(default=None, description="Rendered DOM HTML string")
    rendered_html: Optional[str] = Field(default=None, description="Alias for html string")
    render_time_ms: float = Field(default=0.0, description="Rendering execution time in ms")
    rendered: bool = Field(default=False, description="True if rendering succeeded")
    error: Optional[str] = Field(default=None, description="Error message if rendering failed")
    reasons: List[str] = Field(default_factory=list, description="Render trigger reasons")

    @model_validator(mode="before")
    @classmethod
    def populate_html_alias(cls, values: Any) -> Any:
        if isinstance(values, dict):
            h = values.get("html") or values.get("rendered_html")
            if h:
                values["html"] = h
                values["rendered_html"] = h
        return values

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class BrowserRenderer:
    """Isolated browser rendering engine utilizing Playwright Chromium."""

    def __init__(
        self,
        browser_type: str = "chromium",
        timeout_seconds: float = 15.0,
        headless: bool = True,
    ):
        self.browser_type_name = browser_type
        self.timeout_seconds = timeout_seconds
        self.headless = headless

    def _render(self, url: str) -> RenderedPageResult:
        """Internal rendering execution method."""
        start_time = time.time()
        timeout_ms = int(self.timeout_seconds * 1000)

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                if self.browser_type_name == "firefox":
                    browser_launcher = p.firefox
                elif self.browser_type_name == "webkit":
                    browser_launcher = p.webkit
                else:
                    browser_launcher = p.chromium

                browser = browser_launcher.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AIReadinessAudit/0.1.0"
                )
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                page.set_default_navigation_timeout(timeout_ms)

                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                
                try:
                    page.wait_for_load_state("networkidle", timeout=2000)
                except Exception:
                    pass

                rendered_html = page.content()
                final_url = page.url
                status_code = response.status if response else 200

                browser.close()
                elapsed_ms = round((time.time() - start_time) * 1000, 2)

                return RenderedPageResult(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    html=rendered_html,
                    render_time_ms=elapsed_ms,
                    rendered=True,
                    error=None,
                )
        except Exception as err:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return RenderedPageResult(
                url=url,
                final_url=None,
                status_code=0,
                html=None,
                render_time_ms=elapsed_ms,
                rendered=False,
                error=str(err),
            )

    def render(self, url: str) -> RenderedPageResult:
        """Renders a single web page using Playwright Chromium with passive observation."""
        try:
            return self._render(url)
        except Exception as err:
            return RenderedPageResult(
                url=url,
                rendered=False,
                error=str(err),
            )

    def render_page(self, url: str) -> RenderedPageResult:
        """Alias for render() method."""
        return self.render(url)
