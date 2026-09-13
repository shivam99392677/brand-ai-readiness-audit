"""General HTML Page Text and Structure Extractor."""

from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.evidence.models import (
    ContactCandidate,
    ContactEvidence,
    DateCandidate,
    DateEvidence,
    Provenance,
)

BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section",
    "article", "header", "footer", "nav", "main", "li", "tr", "td", "th", "br", "blockquote"
}

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}

FRAMEWORK_PAYLOAD_PATTERNS = [
    r"self\.__next_f",
    r"__NEXT_DATA__",
    r"__webpack_require__",
    r"Next\.Metadata",
    r"chunk[a-zA-Z0-9_-]+\.js",
]

# Regex patterns for contact signals and dates
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_REGEX = r"\+?\b(?:\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"
DATE_REGEX = r"\b(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? (?:19|20)\d{2}\b"


class GeneralPageHTMLParser(HTMLParser):
    """General-purpose HTML Parser extracting clean visible text, headings, paragraphs, lists, tables, blockquotes, and captions."""

    def __init__(self):
        super().__init__()
        self.headings: List[Dict[str, str]] = []
        self.paragraphs: List[str] = []
        self.lists: List[List[str]] = []
        self.tables: List[Dict[str, Any]] = []
        self.blockquotes: List[str] = []
        self.captions: List[str] = []
        self.sections_found: Set[str] = set()

        self._text_chunks: List[str] = []
        self._tag_stack: List[str] = []

        # Buffers
        self._current_heading_tag: Optional[str] = None
        self._heading_buffer: List[str] = []

        self._in_paragraph = False
        self._paragraph_buffer: List[str] = []

        self._in_blockquote = False
        self._blockquote_buffer: List[str] = []

        self._in_caption = False
        self._caption_buffer: List[str] = []

        self._in_list = False
        self._current_list: List[str] = []
        self._in_list_item = False
        self._list_item_buffer: List[str] = []

        self._in_table = False
        self._table_rows: List[List[str]] = []
        self._current_row: List[str] = []
        self._in_cell = False
        self._cell_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        if tag_lower not in VOID_TAGS:
            self._tag_stack.append(tag_lower)

        if tag_lower in ("main", "article", "nav", "header", "footer", "section"):
            self.sections_found.add(tag_lower)

        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._current_heading_tag = tag_lower
            self._heading_buffer = []
        elif tag_lower == "p":
            self._in_paragraph = True
            self._paragraph_buffer = []
        elif tag_lower == "blockquote":
            self._in_blockquote = True
            self._blockquote_buffer = []
        elif tag_lower in ("figcaption", "caption"):
            self._in_caption = True
            self._caption_buffer = []
        elif tag_lower in ("ul", "ol"):
            self._in_list = True
            self._current_list = []
        elif tag_lower == "li" and self._in_list:
            self._in_list_item = True
            self._list_item_buffer = []
        elif tag_lower == "table":
            self._in_table = True
            self._table_rows = []
        elif tag_lower == "tr" and self._in_table:
            self._current_row = []
        elif tag_lower in ("td", "th") and self._in_table:
            self._in_cell = True
            self._cell_buffer = []

        if tag_lower in BLOCK_TAGS and not any(t in SKIP_TAGS for t in self._tag_stack):
            self._text_chunks.append(" ")

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if self._tag_stack and self._tag_stack[-1] == tag_lower:
            self._tag_stack.pop()

        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6") and self._current_heading_tag == tag_lower:
            h_text = "".join(self._heading_buffer).strip()
            if h_text:
                self.headings.append({"tag": tag_lower, "text": h_text})
            self._current_heading_tag = None
        elif tag_lower == "p" and self._in_paragraph:
            p_text = "".join(self._paragraph_buffer).strip()
            if p_text:
                self.paragraphs.append(p_text)
            self._in_paragraph = False
        elif tag_lower == "blockquote" and self._in_blockquote:
            bq_text = "".join(self._blockquote_buffer).strip()
            if bq_text:
                self.blockquotes.append(bq_text)
            self._in_blockquote = False
        elif tag_lower in ("figcaption", "caption") and self._in_caption:
            cap_text = "".join(self._caption_buffer).strip()
            if cap_text:
                self.captions.append(cap_text)
            self._in_caption = False
        elif tag_lower == "li" and self._in_list_item:
            li_text = "".join(self._list_item_buffer).strip()
            if li_text and self._in_list:
                self._current_list.append(li_text)
            self._in_list_item = False
        elif tag_lower in ("ul", "ol") and self._in_list:
            if self._current_list:
                self.lists.append(self._current_list)
            self._in_list = False
        elif tag_lower in ("td", "th") and self._in_cell:
            cell_text = "".join(self._cell_buffer).strip()
            self._current_row.append(cell_text)
            self._in_cell = False
        elif tag_lower == "tr" and self._in_table:
            if self._current_row:
                self._table_rows.append(self._current_row)
        elif tag_lower == "table" and self._in_table:
            if self._table_rows:
                self.tables.append({"rows": self._table_rows})
            self._in_table = False

        if tag_lower in BLOCK_TAGS and not any(t in SKIP_TAGS for t in self._tag_stack):
            self._text_chunks.append(" ")

    def handle_data(self, data: str):
        if not data:
            return

        if any(t in SKIP_TAGS for t in self._tag_stack):
            return

        for pat in FRAMEWORK_PAYLOAD_PATTERNS:
            if re.search(pat, data):
                return

        if self._current_heading_tag:
            self._heading_buffer.append(data)
        if self._in_paragraph:
            self._paragraph_buffer.append(data)
        if self._in_blockquote:
            self._blockquote_buffer.append(data)
        if self._in_caption:
            self._caption_buffer.append(data)
        if self._in_list_item:
            self._list_item_buffer.append(data)
        if self._in_cell:
            self._cell_buffer.append(data)

        self._text_chunks.append(data)

    def flush_open_buffers(self):
        """Flushes any open tag buffers if tags were not cleanly closed in malformed HTML."""
        if self._current_heading_tag and self._heading_buffer:
            h_text = "".join(self._heading_buffer).strip()
            if h_text:
                self.headings.append({"tag": self._current_heading_tag, "text": h_text})
            self._current_heading_tag = None
            self._heading_buffer = []

        if self._in_paragraph and self._paragraph_buffer:
            p_text = "".join(self._paragraph_buffer).strip()
            if p_text:
                self.paragraphs.append(p_text)
            self._in_paragraph = False
            self._paragraph_buffer = []

        if self._in_blockquote and self._blockquote_buffer:
            bq_text = "".join(self._blockquote_buffer).strip()
            if bq_text:
                self.blockquotes.append(bq_text)
            self._in_blockquote = False
            self._blockquote_buffer = []

        if self._in_caption and self._caption_buffer:
            cap_text = "".join(self._caption_buffer).strip()
            if cap_text:
                self.captions.append(cap_text)
            self._in_caption = False
            self._caption_buffer = []

    def close(self):
        super().close()
        self.flush_open_buffers()

    def get_text(self) -> Tuple[str, str]:
        self.flush_open_buffers()
        raw_text = "".join(self._text_chunks)
        normalized = " ".join(raw_text.split())
        return raw_text, normalized


def extract_page_content(html_content: str, url: str) -> Dict[str, Any]:
    """Extracts structured text content, headings, paragraphs, lists, tables, blockquotes, captions, dates, and contact candidates."""
    parser = GeneralPageHTMLParser()
    try:
        parser.feed(html_content)
        parser.close()
    except Exception:
        pass

    raw_text, normalized_text = parser.get_text()

    # Extract contact candidates
    emails = sorted(list(set(re.findall(EMAIL_REGEX, normalized_text))))
    raw_phones = re.findall(PHONE_REGEX, normalized_text)

    def _is_plausible_phone(candidate: str) -> bool:
        """Filters out non-phone digit sequences (year ranges, version strings, IDs).

        A plausible phone number must either:
        - start with '+' (international format), or
        - contain parentheses (US-style area code), or
        - have exactly 10-11 digits in phone-like grouping, AND
        - must NOT look like a year range (e.g. 1998-2001) or a dotted version string.
        """
        c = candidate.strip()
        digits = re.sub(r"\D", "", c)
        if len(digits) < 10 or len(digits) > 15:
            return False
        # Reject year ranges: two 4-digit year-like tokens (19xx/20xx) joined by a separator
        if re.fullmatch(r"(?:19|20)\d{2}\s*[-\u2013]\s*(?:19|20)\d{2}", c):
            return False
        # Reject dotted version strings (e.g. 3.11.4.1) — phones use -, space, or ()
        if re.fullmatch(r"[\d.]+", c) and c.count(".") >= 2:
            return False
        if c.startswith("+") or "(" in c:
            return True
        # Bare sequences MUST contain a separator (dash/space) between groups —
        # contiguous 10-11 digit runs in prose are IDs/counts, not phones.
        if re.search(r"\d[-\s]\d", c):
            return len(digits) in (10, 11, 12, 13)
        return False

    phones = sorted(list(set(p.strip() for p in raw_phones if _is_plausible_phone(p))))

    contact_candidates: List[ContactCandidate] = []
    provenance_list: List[Provenance] = []

    for email in emails:
        prov = Provenance(source_url=url, location="DOM Text", context=f"email:{email}")
        contact_candidates.append(ContactCandidate(value=email, candidate_type="email", provenance=prov))
        provenance_list.append(prov)

    for phone in phones:
        prov = Provenance(source_url=url, location="DOM Text", context=f"phone:{phone}")
        contact_candidates.append(ContactCandidate(value=phone, candidate_type="phone", provenance=prov))
        provenance_list.append(prov)

    contacts = ContactEvidence(
        emails=emails,
        phone_numbers=phones,
        addresses=[],
        candidates=contact_candidates,
        provenance_list=provenance_list,
    )

    # Extract date candidates
    visible_dates = sorted(list(set(re.findall(DATE_REGEX, normalized_text))))
    date_candidates: List[DateCandidate] = []
    for d_val in visible_dates:
        prov = Provenance(source_url=url, location="DOM Text", context=f"visible_date:{d_val}")
        date_candidates.append(DateCandidate(value=d_val, candidate_type="visible_date", provenance=prov))

    dates = DateEvidence(
        visible_dates=visible_dates,
        machine_dates={},
        candidates=date_candidates,
    )

    return {
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "word_count": len(normalized_text.split()),
        "headings": parser.headings,
        "paragraphs": parser.paragraphs,
        "lists": parser.lists,
        "tables": parser.tables,
        "blockquotes": parser.blockquotes,
        "captions": parser.captions,
        "sections_found": sorted(list(parser.sections_found)),
        "contacts": contacts,
        "dates": dates,
    }
