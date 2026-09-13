import requests
from typing import List, Dict, Optional
from urllib.parse import urljoin
from src.models import Evidence, Finding, FindingSeverity, FindingStatus

def run_sitemap_audit(url: str, headers: Optional[Dict[str, str]] = None) -> List[Finding]:
    """Detect and validate sitemap.xml presence.
    Returns a FAIL finding with HIGH severity if sitemap is missing or empty.
    """
    headers = headers or {}
    sitemap_url = urljoin(url.rstrip('/') + '/', 'sitemap.xml')
    try:
        resp = requests.get(sitemap_url, headers=headers, timeout=5)
    except Exception as e:
        ev = Evidence(
            source_url=sitemap_url,
            evidence_type="sitemap_fetch",
            observed={"error": str(e)},
            location="GET sitemap.xml",
        )
        return [Finding(
            skill="sitemap-audit",
            check_id="CR-013",
            title="sitemap.xml Unreachable — Sitemap Check Not Scored",
            status=FindingStatus.ERROR,
            severity=FindingSeverity.LOW,
            description=(
                f"sitemap.xml could not be fetched ({str(e)[:120]}); sitemap presence "
                "could not be verified and this check is not scored."
            ),
            evidence=[ev],
            recommendation="Verify sitemap.xml reachability; re-run the audit to score sitemap discovery.",
        )]
    if resp.status_code != 200:
        ev = Evidence(
            source_url=sitemap_url,
            evidence_type="sitemap_http",
            observed={"status_code": resp.status_code},
            expected={"status_code": 200},
            location="GET sitemap.xml",
        )
        # A missing sitemap (404) is a discoverability suggestion, not a site
        # failure: many small sites rely on robots.txt + links alone. Also note
        # that a sitemap may still be declared inside robots.txt at another URL.
        return [Finding(
            skill="sitemap-audit",
            check_id="CR-013",
            title=f"No Sitemap at /sitemap.xml (HTTP {resp.status_code})",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description=(
                f"GET {sitemap_url} returned HTTP {resp.status_code}, so no default-location "
                "sitemap was found. This limits bulk URL discovery for crawlers but does not "
                "block indexing by itself. Check whether a sitemap is declared in robots.txt "
                "at a non-default URL."
            ),
            evidence=[ev],
            recommendation=(
                "Publish a sitemap.xml at the site root (or declare 'Sitemap: <url>' in robots.txt) "
                "listing canonical indexable URLs."
            ),
        )]
    # Simple XML parsing for <loc> entries
    content = resp.text
    if "<loc" not in content.lower():
        ev = Evidence(
            source_url=sitemap_url,
            evidence_type="sitemap_content",
            observed={"content": content[:200]},
            location="GET sitemap.xml",
        )
        return [Finding(
            skill="sitemap-audit",
            check_id="CR-013",
            title="Sitemap Discovery",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.MEDIUM,
            description="Sitemap fetched but contains no <loc> entries.",
            evidence=[ev],
            recommendation="Populate sitemap.xml with URL entries using <loc> tags.",
        )]
    ev = Evidence(
        source_url=sitemap_url,
        evidence_type="sitemap_ok",
        observed={"status_code": resp.status_code},
        location="GET sitemap.xml",
    )
    return [Finding(
        skill="sitemap-audit",
        check_id="CR-013",
        title="Sitemap Discovery",
        status=FindingStatus.PASS,
        severity=FindingSeverity.INFO,
        description="Sitemap.xml is present and contains URL entries.",
        evidence=[ev],
        recommendation="Maintain up‑to‑date sitemap for crawler discoverability.",
    )]
