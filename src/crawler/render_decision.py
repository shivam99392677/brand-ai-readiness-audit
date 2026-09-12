"""Selective Playwright rendering decision engine.

Evaluates objective page signals to determine whether browser DOM rendering
is necessary, avoiding redundant browser rendering for static HTTP content.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

FRAMEWORK_CONTAINER_IDS = {"root", "app", "__next", "__nuxt"}


class RenderDecision(BaseModel):
    """Result of render decision evaluation."""
    should_render: bool = Field(..., description="True if browser rendering is required")
    reasons: List[str] = Field(default_factory=list, description="Objective trigger reasons")

    @property
    def required(self) -> bool:
        return self.should_render


def should_render_page(
    url: str,
    html_content: str = "",
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None,
    http_status: Optional[int] = None,
    word_count: Optional[int] = None,
    raw_text_len: Optional[int] = None,
    links_count: Optional[int] = None,
    html: Optional[str] = None,
    **kwargs: Any,
) -> RenderDecision:
    """Evaluates objective signals to decide if browser rendering is necessary.

    Per Requirement 3: Framework markers (e.g. #__next, #root, #app) ALONE are NOT proof
    that browser rendering is required. Rendering is triggered based on a combination
    of objective signals, especially whether the HTTP response exposes substantially
    less content than expected.
    """
    reasons: List[str] = []
    actual_status = http_status if http_status is not None else status_code
    actual_html = html if html is not None else html_content

    if actual_status != 200:
        return RenderDecision(should_render=False, reasons=[])

    if not actual_html or not actual_html.strip():
        return RenderDecision(should_render=True, reasons=["HTTP body empty"])

    # Extract clean visible body text (exclude head, script, style, noscript, svg)
    clean_text = re.sub(r'<(head|script|style|noscript|svg)[^>]*>.*?</\1>', '', actual_html, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
    words = clean_text.split()
    visible_words = len(words) if word_count is None else word_count

    # 1. Framework shell container detection
    found_cid = None
    for cid in FRAMEWORK_CONTAINER_IDS:
        t1 = f'id="{cid}"'
        t2 = f"id='{cid}'"
        if t1 in actual_html or t2 in actual_html:
            found_cid = cid
            break

    # Check if container element is empty in the HTML source
    container_is_empty = False
    if found_cid:
        empty_pattern = rf'<[a-zA-Z0-9]+\s+[^>]*\bid=["\']{re.escape(found_cid)}["\'][^>]*>\s*(<!--.*?-->)?\s*</[a-zA-Z0-9]+>'
        if re.search(empty_pattern, actual_html, flags=re.DOTALL | re.IGNORECASE):
            container_is_empty = True

    # Combination Rule (Requirement 3):
    # Framework container triggers rendering ONLY IF container is empty OR visible HTTP text is low (< 30 words)
    if found_cid and (container_is_empty or visible_words < 30):
        reasons.append(f"Empty app container: #{found_cid}")
    elif visible_words < 30 and not found_cid:
        # Low word count alone without container tag
        reasons.append(f"Low HTTP visible word count ({visible_words} < 30 words)")

    # 2. Check script-to-text ratio (> 5.0) when visible text is low (< 50 words)
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', actual_html, flags=re.DOTALL | re.IGNORECASE)
    script_char_count = sum(len(s) for s in scripts)
    visible_char_count = sum(len(w) for w in words)
    if visible_words < 50 and visible_char_count > 0:
        ratio = script_char_count / visible_char_count
        if ratio > 5.0:
            reasons.append(f"High script-to-text ratio ({ratio:.1f} > 5.0)")

    # 3. Check noscript JS required warning when visible text is low (< 50 words)
    if "<noscript" in actual_html.lower() and ("javascript" in actual_html.lower() or "enable js" in actual_html.lower() or "requires javascript" in actual_html.lower()):
        if visible_words < 50:
            reasons.append("Contains <noscript> JavaScript warning")

    should_render = len(reasons) > 0
    return RenderDecision(should_render=should_render, reasons=reasons)

