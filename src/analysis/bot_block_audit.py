import requests
from typing import List, Dict, Optional
from urllib.parse import urljoin
from src.models import Evidence, Finding, FindingSeverity, FindingStatus

def run_bot_block_audit(url: str, headers: Optional[Dict[str, str]] = None) -> List[Finding]:
    """Check robots.txt for AI bot disallow rules.
    Flags HIGH severity FAIL if any target bot is explicitly disallowed.
    """
    headers = headers or {}
    robots_url = urljoin(url.rstrip('/') + '/', 'robots.txt')
    try:
        resp = requests.get(robots_url, headers=headers, timeout=5)
    except Exception as e:
        ev = Evidence(
            source_url=robots_url,
            evidence_type="robots_fetch",
            observed={"error": str(e)},
            location="GET robots.txt",
        )
        return [Finding(
            skill="bot-block-audit",
            check_id="CR-014",
            title="robots.txt Unreachable — Bot Blocking Not Scored",
            status=FindingStatus.ERROR,
            severity=FindingSeverity.LOW,
            description=(
                f"robots.txt could not be fetched ({str(e)[:120]}); whether AI bots are blocked "
                "could not be verified and this check is not scored."
            ),
            evidence=[ev],
            recommendation="Verify robots.txt reachability; re-run the audit to score bot access rules.",
        )]
    if resp.status_code != 200:
        ev = Evidence(
            source_url=robots_url,
            evidence_type="robots_http",
            observed={"status_code": resp.status_code},
            expected={"status_code": 200},
            location="GET robots.txt",
        )
        # A missing/forbidden robots.txt is NOT evidence that AI bots are blocked:
        # crawlers fall back to default rules. Report reachability only (LOW/INFO),
        # and never under the "AI Bot Blocking" title (which requires explicit
        # Disallow rules to be factually true).
        return [Finding(
            skill="bot-block-audit",
            check_id="CR-014",
            title=f"robots.txt Not Accessible (HTTP {resp.status_code})",
            status=FindingStatus.WARNING,
            severity=FindingSeverity.LOW,
            description=(
                f"robots.txt returned HTTP {resp.status_code}. No explicit AI-bot rules were "
                "found (the file does not exist or is not served); AI crawler access defaults apply. "
                "This is a reachability observation, not confirmed bot blocking."
            ),
            evidence=[ev],
            recommendation=(
                "Optionally publish a robots.txt at the site root declaring explicit AI bot rules "
                "(GPTBot, ClaudeBot, PerplexityBot) so crawler access is intentional and auditable."
            ),
        )]
    content = resp.text.lower()
    target_bots = ["gptbot", "claudebot", "perplexitybot", "google-extended"]
    blocked = []
    for bot in target_bots:
        pattern = f"user-agent: {bot}\n"
        if pattern in content:
            # find Disallow line following this user-agent
            start = content.find(pattern) + len(pattern)
            rest = content[start:]
            for line in rest.splitlines():
                if line.startswith("user-agent"):
                    break
                if line.startswith("disallow"):
                    if "/" in line.split(":", 1)[1].strip():
                        blocked.append(bot)
                    break
    if blocked:
        ev = Evidence(
            source_url=robots_url,
            evidence_type="robots_block",
            observed={"blocked_bots": blocked},
            location="robots.txt",
        )
        return [Finding(
            skill="bot-block-audit",
            check_id="CR-014",
            title="AI Bot Blocking via robots.txt",
            status=FindingStatus.FAIL,
            severity=FindingSeverity.HIGH,
            description=f"robots.txt explicitly disallows AI bots: {', '.join(blocked)}.",
            evidence=[ev],
            recommendation="Remove Disallow rules for AI bots to allow indexing.",
        )]
    ev = Evidence(
        source_url=robots_url,
        evidence_type="robots_ok",
        observed={"status_code": resp.status_code},
        location="robots.txt",
    )
    return [Finding(
        skill="bot-block-audit",
        check_id="CR-014",
        title="AI Bot Blocking via robots.txt",
        status=FindingStatus.PASS,
        severity=FindingSeverity.INFO,
        description="robots.txt does not block target AI bots.",
        evidence=[ev],
        recommendation="No changes needed.",
    )]
