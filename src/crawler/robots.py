"""Robots.txt parser and checker returning structured RobotsEvidence and rule groups."""

import urllib.robotparser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import requests

from src.evidence.models import RobotsEvidence, UserAgentRuleGroup


class RobotsChecker:
    """Fetches and parses robots.txt to verify crawler permissions, user-agent groups, and sitemap declarations."""

    def __init__(self, user_agent: str = "AIReadinessAudit/0.1.0", timeout: float = 3.0):
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch_and_parse(self, target_url: str) -> RobotsEvidence:
        """Fetches robots.txt and returns structured RobotsEvidence."""
        res = self.check_robots(target_url)
        return res["evidence"]

    def is_allowed(self, url: str, robots_evidence: Optional[RobotsEvidence] = None) -> bool:
        """Checks if a URL is allowed by robots.txt rules."""
        if robots_evidence and hasattr(robots_evidence, "available"):
            if not robots_evidence.available:
                return True
        res = self.check_robots(url)
        return res.get("allowed", True)

    def check_robots(self, target_url: str) -> Dict[str, Any]:
        """Fetches robots.txt for target domain and returns structured robots check dictionary and RobotsEvidence."""
        parsed = urlparse(target_url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

        status_code = 0
        exists = False
        allowed = True
        sitemaps_declared: List[str] = []
        user_agent_groups: List[UserAgentRuleGroup] = []
        parse_errors: List[str] = []

        try:
            resp = requests.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            status_code = resp.status_code
            if resp.status_code == 200:
                exists = True
                content = resp.text

                # Parse user-agent blocks & sitemaps
                user_agent_groups, sitemaps_declared, _, _, _ = parse_robots_txt_rules(content)

                rp = urllib.robotparser.RobotFileParser()
                rp.parse(content.splitlines())
                allowed = rp.can_fetch(self.user_agent, target_url)
            else:
                exists = False
                allowed = True
        except Exception as err:
            exists = False
            allowed = True
            parse_errors.append(str(err))

        robots_evidence = RobotsEvidence(
            url=robots_url,
            available=exists,
            status_code=status_code,
            user_agent_groups=user_agent_groups,
            sitemaps_declared=sitemaps_declared,
            parse_errors=parse_errors,
        )

        result: Dict[str, Any] = {
            "checked": True,
            "url": robots_url,
            "found": exists,
            "allowed": allowed,
            "sitemaps_declared": sitemaps_declared,
            "error": parse_errors[0] if parse_errors else None,
            "evidence": robots_evidence,
        }

        return result


def parse_robots_txt_rules(content: str) -> Tuple[List[UserAgentRuleGroup], List[str], List[str], List[str], Optional[float]]:
    """Parses robots.txt line-by-line into structured UserAgentRuleGroup blocks preserving multi-user-agent groups.
    
    Returns (user_agent_groups, sitemaps_declared, aggregate_allows, aggregate_disallows, crawl_delay).
    """
    groups: List[UserAgentRuleGroup] = []
    sitemaps: List[str] = []
    all_allows: List[str] = []
    all_disallows: List[str] = []
    global_crawl_delay: Optional[float] = None

    current_agents: List[str] = []
    current_allows: List[str] = []
    current_disallows: List[str] = []
    current_delay: Optional[float] = None
    has_rules = False

    def flush_group():
        nonlocal current_agents, current_allows, current_disallows, current_delay, has_rules
        if current_agents:
            groups.append(UserAgentRuleGroup(
                user_agents=list(current_agents),
                allow=list(current_allows),
                disallow=list(current_disallows),
                crawl_delay=current_delay,
            ))
            current_agents = []
            current_allows = []
            current_disallows = []
            current_delay = None
            has_rules = False

    for line in content.splitlines():
        line_clean = line.split("#")[0].strip()
        if not line_clean:
            continue

        if ":" in line_clean:
            key, val = line_clean.split(":", 1)
            key_lower = key.strip().lower()
            val_clean = val.strip()

            if key_lower == "user-agent":
                if has_rules:
                    flush_group()
                current_agents.append(val_clean)
            elif key_lower == "allow":
                if val_clean:
                    current_allows.append(val_clean)
                    all_allows.append(val_clean)
                    has_rules = True
            elif key_lower == "disallow":
                if val_clean:
                    current_disallows.append(val_clean)
                    all_disallows.append(val_clean)
                    has_rules = True
            elif key_lower == "crawl-delay":
                try:
                    current_delay = float(val_clean)
                    if global_crawl_delay is None:
                        global_crawl_delay = current_delay
                    has_rules = True
                except ValueError:
                    pass
            elif key_lower == "sitemap":
                if val_clean and val_clean not in sitemaps:
                    sitemaps.append(val_clean)

    flush_group()

    return groups, sitemaps, all_allows, all_disallows, global_crawl_delay
