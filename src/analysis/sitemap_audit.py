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
            title="Sitemap Discovery",
            status=FindingStatus.ERROR,
            severity=FindingSeverity.HIGH,
            description="Failed to fetch sitemap.xml due to network error.",
            evidence=[ev],
            recommendation="Ensure sitemap.xml is reachable and served without errors.",
        )]
    if resp.status_code != 200:
        ev = Evidence(
            source_url=sitemap_url,
            evidence_type="sitemap_http",
            observed={"status_code": resp.status_code},
            expected={"status_code": 200},
            location="GET sitemap.xml",
        )
        return [Finding(
            skill="sitemap-audit",
            check_id="CR-013",
            title="Sitemap Discovery",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description=f"Sitemap request returned status {resp.status_code}, expected 200.",
            evidence=[ev],
            recommendation="Provide a valid sitemap.xml accessible at the site root.",
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
