"""Common Evidence and Finding Model for Brand AI Readiness Audit."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class FindingStatus(str, Enum):
    """Supported audit check status values."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"
    INFO = PASS



class FindingSeverity(str, Enum):
    """Supported audit check severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Evidence(BaseModel):
    """Structured and traceable evidence backing an audit finding."""
    source_url: str = Field(..., description="Target or source URL where evidence was gathered")
    evidence_type: str = Field(..., description="Category of evidence (e.g., dom_snapshot, http_header, schema_jsonld)")
    observed: Any = Field(..., description="Raw observed evidence payload, text, or data structure")
    expected: Optional[Any] = Field(default=None, description="Expected value, pattern, or baseline state")
    location: Optional[str] = Field(default=None, description="Location pointer (DOM selector, JSON path, header name)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")

    @field_validator("source_url", "evidence_type")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("observed")
    @classmethod
    def validate_observed_present(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Observed evidence cannot be None.")
        return v


class Finding(BaseModel):
    """Single audit finding representing the result of a specific skill check."""
    skill: str = Field(..., description="ID of the skill that executed the check")
    check_id: str = Field(..., description="Unique check identifier within the skill")
    title: str = Field(..., description="Short descriptive title of the check")
    status: FindingStatus = Field(..., description="Status of the audit check")
    severity: FindingSeverity = Field(..., description="Severity level of the check result")
    description: str = Field(..., description="Detailed description of the finding")
    evidence: List[Evidence] = Field(..., description="Structured evidence items backing this finding")
    recommendation: str = Field(..., description="Actionable remediation recommendation")

    @field_validator("skill", "check_id", "title", "description", "recommendation")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Text fields cannot be empty or whitespace.")
        return v.strip()

    @field_validator("evidence")
    @classmethod
    def validate_evidence_list(cls, v: List[Evidence]) -> List[Evidence]:
        if not isinstance(v, list):
            raise ValueError("Evidence must be a list of Evidence objects.")
        return v


class AuditSummary(BaseModel):
    """Summary of audit execution metrics and overall score."""
    total_checks: int = Field(..., ge=0, description="Total number of checks executed")
    passed: int = Field(..., ge=0, description="Number of passed checks")
    failed: int = Field(..., ge=0, description="Number of failed checks")
    warnings: int = Field(..., ge=0, description="Number of warning checks")
    errors: int = Field(..., ge=0, description="Number of errored checks")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Deterministic overall readiness score (0-100)")


def calculate_summary(findings: List[Finding], critical_cap: float = 40.0) -> AuditSummary:
    """Deterministically calculates audit summary metrics and readiness score from findings."""
    total_checks = len(findings)
    passed = sum(1 for f in findings if f.status == FindingStatus.PASS)
    failed = sum(1 for f in findings if f.status == FindingStatus.FAIL)
    warnings = sum(1 for f in findings if f.status == FindingStatus.WARNING)
    errors = sum(1 for f in findings if f.status == FindingStatus.ERROR)

    scored_findings = [
        f for f in findings
        if f.status in (FindingStatus.PASS, FindingStatus.FAIL, FindingStatus.WARNING, FindingStatus.ERROR)
    ]

    if not scored_findings:
        overall_score = 100.0
    else:
        severity_weights = {
            FindingSeverity.CRITICAL: 2.0,
            FindingSeverity.HIGH: 1.5,
            FindingSeverity.MEDIUM: 1.0,
            FindingSeverity.LOW: 0.5,
            FindingSeverity.INFO: 0.2,
        }

        total_weight = 0.0
        max_possible_weight = 0.0

        for f in scored_findings:
            w = severity_weights.get(f.severity, 1.0)
            max_possible_weight += w
            if f.status == FindingStatus.PASS:
                total_weight += w
            elif f.status == FindingStatus.WARNING:
                total_weight += w * 0.5

        raw_score = (total_weight / max_possible_weight) * 100.0 if max_possible_weight > 0 else 100.0

        has_critical_failure = any(
            f.severity == FindingSeverity.CRITICAL and f.status in (FindingStatus.FAIL, FindingStatus.ERROR)
            for f in findings
        )

        if has_critical_failure:
            overall_score = min(raw_score, critical_cap)
        else:
            overall_score = raw_score

    overall_score = round(max(0.0, min(100.0, overall_score)), 2)

    return AuditSummary(
        total_checks=total_checks,
        passed=passed,
        failed=failed,
        warnings=warnings,
        errors=errors,
        overall_score=overall_score,
    )


class AuditReport(BaseModel):
    """Complete Audit Report structure containing top-level crawl manifest, findings, and aggregated summary."""
    url: str = Field(..., description="Audited website URL")
    timestamp: str = Field(..., description="ISO 8601 audit execution timestamp")
    crawl: Optional[Any] = Field(default=None, description="Site-wide crawl manifest and page evidence store")
    skills_run: List[str] = Field(..., description="List of skill IDs executed")
    findings: List[Finding] = Field(default_factory=list, description="List of audit findings")
    summary: AuditSummary = Field(..., description="Deterministic audit summary")

    @classmethod
    def create(
        cls,
        url: str,
        skills_run: List[str],
        findings: List[Finding],
        crawl: Optional[Any] = None,
        timestamp: Optional[str] = None,
        critical_cap: float = 40.0,
    ) -> "AuditReport":
        """Factory method to build an AuditReport with auto-computed summary and optional crawl manifest."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        summary = calculate_summary(findings, critical_cap=critical_cap)
        return cls(
            url=url,
            timestamp=ts,
            crawl=crawl,
            skills_run=skills_run,
            findings=findings,
            summary=summary,
        )
