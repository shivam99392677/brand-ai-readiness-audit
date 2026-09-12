"""Sitemap discovery, index parsing, and SitemapEvidence generation module."""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import requests

from src.crawler.url_utils import normalize_url, is_crawlable_html_url
from src.evidence.models import SitemapEntry, SitemapEvidence


class SitemapDiscoverer:
    """Discovers and parses XML sitemaps (<urlset> and <sitemapindex>), generating structured SitemapEvidence."""

    def __init__(self, user_agent: str = "AIReadinessAudit/0.1.0", timeout: float = 3.0):
        self.user_agent = user_agent
        self.timeout = timeout

    def discover_sitemap_urls(
        self,
        target_url: str,
        declared_sitemaps: Optional[List[str]] = None,
        base_domain: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Checks for sitemap.xml and declared sitemaps, returning structured metadata and discovered URLs."""
        parsed_target = urlparse(target_url)
        default_sitemap = urljoin(f"{parsed_target.scheme}://{parsed_target.netloc}", "/sitemap.xml")

        candidates_to_check = list(declared_sitemaps or [])
        if default_sitemap not in candidates_to_check:
            candidates_to_check.append(default_sitemap)

        discovered_urls: Set[str] = set()
        sitemap_evidence_list: List[SitemapEvidence] = []
        sitemap_found = False
        primary_sitemap_url = candidates_to_check[0] if candidates_to_check else default_sitemap

        for sm_url in candidates_to_check:
            sm_ev, urls = self._fetch_and_parse_sitemap(sm_url, base_domain=base_domain)
            sitemap_evidence_list.append(sm_ev)
            if sm_ev.status_code == 200:
                sitemap_found = True
                discovered_urls.update(urls)

        evidence = {
            "checked": True,
            "found": sitemap_found,
            "url": primary_sitemap_url,
            "urls_discovered": len(discovered_urls),
            "sitemap_evidence_items": sitemap_evidence_list,
        }

        return evidence, sorted(list(discovered_urls))

    def fetch_and_parse(self, sitemap_url: str, base_domain: Optional[str] = None) -> SitemapEvidence:
        """Fetches a sitemap URL and returns a SitemapEvidence object."""
        sm_ev, _ = self._fetch_and_parse_sitemap(sitemap_url, base_domain=base_domain)
        return sm_ev

    def _fetch_and_parse_sitemap(
        self,
        sitemap_url: str,
        base_domain: Optional[str] = None,
    ) -> Tuple[SitemapEvidence, List[str]]:
        """Fetches a single sitemap URL and returns a SitemapEvidence object and list of page URLs."""
        status_code = 0
        is_index = False
        child_indices: List[str] = []
        page_urls: List[str] = []
        lastmod_map: Dict[str, str] = {}
        parse_errors: List[str] = []

        try:
            resp = requests.get(
                sitemap_url,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            status_code = resp.status_code
            if resp.status_code == 200 and resp.text.strip():
                is_index, child_indices, page_urls, lastmod_map = parse_sitemap_xml_details(
                    xml_content=resp.text,
                    sitemap_url=sitemap_url,
                    base_domain=base_domain,
                )
        except Exception as err:
            status_code = 0
            parse_errors.append(str(err))

        entries = [SitemapEntry(url=u, lastmod=lastmod_map.get(u)) for u in page_urls]

        sm_ev = SitemapEvidence(
            url=sitemap_url,
            status_code=status_code,
            type="sitemapindex" if is_index else "urlset",
            entries=entries,
            sitemap_indices=child_indices,
            parse_errors=parse_errors,
        )

        return sm_ev, page_urls


def parse_sitemap_xml_details(
    xml_content: str,
    sitemap_url: str = "",
    base_domain: Optional[str] = None,
) -> Tuple[bool, List[str], List[str], Dict[str, str]]:
    """Parses raw XML string content of a sitemap or sitemap index.
    
    Returns (is_index, child_sitemap_urls, target_page_urls, lastmod_mapping).
    """
    is_index = False
    child_indices: List[str] = []
    page_urls: Set[str] = set()
    lastmod_map: Dict[str, str] = {}

    try:
        root = ET.fromstring(xml_content)
        tag_name = root.tag.split("}")[-1].lower() if "}" in root.tag else root.tag.lower()

        if tag_name == "sitemapindex":
            is_index = True
            for elem in root.iter():
                elem_tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
                if elem_tag == "loc" and elem.text and elem.text.strip():
                    sm_loc = normalize_url(elem.text.strip(), base_url=sitemap_url)
                    if sm_loc:
                        child_indices.append(sm_loc)
        elif tag_name == "urlset":
            is_index = False
            for child in root:
                child_tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
                if child_tag == "url":
                    loc_val: Optional[str] = None
                    lastmod_val: Optional[str] = None
                    for sub in child:
                        sub_tag = sub.tag.split("}")[-1].lower() if "}" in sub.tag else sub.tag.lower()
                        if sub_tag == "loc" and sub.text and sub.text.strip():
                            loc_val = sub.text.strip()
                        elif sub_tag == "lastmod" and sub.text and sub.text.strip():
                            lastmod_val = sub.text.strip()
                    
                    if loc_val:
                        norm = normalize_url(loc_val, base_url=sitemap_url)
                        if norm and norm not in page_urls and is_crawlable_html_url(norm, base_domain=base_domain):
                            page_urls.add(norm)
                            if lastmod_val:
                                lastmod_map[norm] = lastmod_val
    except Exception:
        pass

    return is_index, sorted(child_indices), sorted(list(page_urls)), lastmod_map


def parse_sitemap_xml(xml_content: str, sitemap_url: str = "", base_domain: Optional[str] = None) -> List[str]:
    """Backward-compatible helper function returning sorted list of target page URLs."""
    _, _, urls, _ = parse_sitemap_xml_details(xml_content=xml_content, sitemap_url=sitemap_url, base_domain=base_domain)
    return urls
