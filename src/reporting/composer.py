"""Adobe Report Composer.

Transforms internal Finding objects and extraction results into the canonical
Adobe Hackathon JSON report schema with strict validation, lowercase severity,
suggested_action object structure, and sequential F-001 IDs.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from src.models import Finding, FindingSeverity, FindingStatus


SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

PRIORITY_MAP = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


class SuggestedAction(BaseModel):
    """Structured remediation action object required by Adobe schema."""
    summary: str = Field(..., description="Actionable remediation guidance")
    priority: str = Field(..., description="Action priority (critical, high, medium, low)")


class AdobeFinding(BaseModel):
    """Adobe-compliant finding record."""
    id: str = Field(..., description="Sequential finding identifier, e.g. F-001")
    title: str = Field(..., description="Descriptive title of the finding")
    severity: str = Field(..., description="Lowercase severity level (critical, high, medium, low)")
    evidence: str = Field(..., description="Traceable factual evidence summary backing the finding")
    suggested_action: SuggestedAction = Field(..., description="Structured action guidance object")
    
    # Optional supplementary metadata
    check_id: Optional[str] = Field(default=None, description="Internal check identifier")
    category: Optional[str] = Field(default=None, description="Audit category")
    why_it_matters: Optional[str] = Field(default=None, description="Impact explanation on AI models")
    affected_urls: Optional[List[str]] = Field(default=None, description="URLs impacted by this finding")


class AdobeSummary(BaseModel):
    """Adobe-compliant summary metrics."""
    total_findings: int = Field(..., ge=0, description="Total defect findings")
    critical: int = Field(default=0, ge=0, description="Count of critical severity findings")
    high: int = Field(default=0, ge=0, description="Count of high severity findings")
    medium: int = Field(default=0, ge=0, description="Count of medium severity findings")
    low: int = Field(default=0, ge=0, description="Count of low severity findings")


class AdobeReport(BaseModel):
    """Top-level Adobe Hackathon report structure."""
    site: str = Field(..., description="Audited domain or hostname")
    audited_at: str = Field(..., description="ISO 8601 audit timestamp")
    summary: AdobeSummary = Field(..., description="Findings count summary")
    findings: List[AdobeFinding] = Field(default_factory=list, description="Ordered defect findings")


class AdobeReportComposer:
    @classmethod
    def compose(cls, target_url: str, findings: List[Finding], timestamp: Optional[str] = None, include_suggestions: bool = True) -> Dict[str, Any]:
        """Convenient wrapper so callers can use AdobeReportComposer.compose(url, findings)."""
        return cls()._compose(target_url, findings, timestamp=timestamp, include_suggestions=include_suggestions)

    """Composes, filters, deduplicates, and formats internal findings into the Adobe Report format."""

    def _compose(
        self,
        target_url: str,
        findings: List[Finding],
        timestamp: Optional[str] = None,
        include_suggestions: bool = True,
    ) -> Dict[str, Any]:
        """Filters, deduplicates, sorts, and compiles findings into Adobe JSON dictionary."""
        # 1. Format site hostname
        parsed = urlparse(target_url)
        site_name = parsed.netloc or target_url

        audit_time = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 2. Filter out PASS, INFO, NOT_APPLICABLE, or findings without evidence
        actionable_findings: List[Finding] = []
        for f in findings:
            if f.status in (FindingStatus.FAIL, FindingStatus.WARNING, FindingStatus.ERROR):
                if f.evidence:
                    actionable_findings.append(f)

        # 3. Deduplicate near-identical findings by (check_id, title)
        deduped_findings: List[Finding] = []
        seen_keys = set()
        for f in actionable_findings:
            key = (f.check_id, f.title.strip().lower())
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_findings.append(f)

        # 3b. Cross-skill semantic dedup: FC-03 and EI-02 both report missing
        # sameAs corroboration. Keep only the first occurrence of the same
        # semantic issue (normalized title match on the sameAs-missing family).
        SAMEAS_MISSING_TITLES = {
            "missing external entity corroboration links",
            "missing canonical sameas social profiles",
        }
        seen_sameas_missing = False
        semantically_deduped: List[Finding] = []
        for f in deduped_findings:
            norm_title = f.title.strip().lower()
            if norm_title in SAMEAS_MISSING_TITLES:
                if seen_sameas_missing:
                    continue  # duplicate of the same missing-sameAs issue
                seen_sameas_missing = True
            semantically_deduped.append(f)
        deduped_findings = semantically_deduped

        # 4. Sort by severity: critical > high > medium > low
        def get_sev_weight(f: Finding) -> int:
            sev_str = f.severity.value.lower() if isinstance(f.severity, FindingSeverity) else str(f.severity).lower()
            return SEVERITY_ORDER.get(sev_str, 99)

        sorted_findings = sorted(deduped_findings, key=get_sev_weight)

        # 5. Format into AdobeFinding objects with sequential F-001 IDs
        adobe_findings_list: List[Dict[str, Any]] = []
        crit_count = 0
        high_count = 0
        med_count = 0
        low_count = 0

        for idx, f in enumerate(sorted_findings, start=1):
            finding_id = f"F-{str(idx).zfill(3)}"
            sev_str = f.severity.value.lower() if isinstance(f.severity, FindingSeverity) else str(f.severity).lower()

            if sev_str == "critical":
                crit_count += 1
            elif sev_str == "high":
                high_count += 1
            elif sev_str == "medium":
                med_count += 1
            elif sev_str == "low":
                low_count += 1

            # Format evidence string from internal Evidence objects
            ev_descriptions = []
            affected_urls = set()
            for ev in f.evidence:
                if ev.source_url:
                    affected_urls.add(ev.source_url)
                if isinstance(ev.observed, dict):
                    obs_str = ", ".join(f"{k}: {v}" for k, v in ev.observed.items() if not str(v).startswith("<!DOCTYPE"))
                    ev_descriptions.append(f"[{ev.location or ev.evidence_type}] {obs_str}" if obs_str else str(ev.evidence_type))
                else:
                    ev_descriptions.append(str(ev.observed))

            evidence_summary = f.description
            # Evidence MUST be traceable: always append observed details so the
            # evidence string carries a URL and/or count.
            if ev_descriptions:
                evidence_summary += f" Observed: {'; '.join(ev_descriptions[:2])}"

            suggested_action = {
                "summary": f.recommendation or "Review and resolve the technical configuration issue.",
                "priority": PRIORITY_MAP.get(sev_str, "medium"),
            }

            adobe_item = {
                "id": finding_id,
                "title": f.title,
                "severity": sev_str,
                "evidence": evidence_summary,
                "suggested_action": suggested_action,
                "check_id": f.check_id,
                "category": f.skill,
                "affected_urls": sorted(list(affected_urls)) if affected_urls else [target_url],
            }
            adobe_findings_list.append(adobe_item)

        # 6. Build Summary
        summary = {
            "total_findings": len(adobe_findings_list),
            "critical": crit_count,
            "high": high_count,
            "medium": med_count,
            "low": low_count,
        }

        adobe_report = {
            "site": site_name,
            "audited_at": audit_time,
            "summary": summary,
            "findings": adobe_findings_list,
        }

        return adobe_report


def compose_adobe_report(
    target_url: str,
    findings: List[Finding],
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper function to compose Adobe report JSON."""
    composer = AdobeReportComposer()
    return composer._compose(target_url=target_url, findings=findings, timestamp=timestamp)


def save_adobe_report(report_dict: Dict[str, Any], filepath: str = "report.json") -> None:
    """Serializes Adobe report dictionary to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
