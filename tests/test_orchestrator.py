"""Unit tests for AuditOrchestrator (src/orchestrator.py)."""

import pytest
from src.models import Finding, FindingSeverity, FindingStatus, Evidence
from src.orchestrator import AuditOrchestrator, validate_target_url


def test_url_validation_valid():
    """Verify URL validation accepts valid HTTP and HTTPS URLs."""
    assert validate_target_url("https://example.com") == "https://example.com"
    assert validate_target_url("http://brand.org/path") == "http://brand.org/path"


def test_url_validation_invalid():
    """Verify URL validation raises ValueError for invalid inputs."""
    with pytest.raises(ValueError, match="Invalid target URL"):
        validate_target_url("invalid-url")

    with pytest.raises(ValueError, match="Target URL must be a non-empty string"):
        validate_target_url("")


def test_orchestrator_invokes_both_skills_and_aggregates_findings():
    """Verify both crawl-render-audit and structured-data-audit skills run and populate report."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Domain</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Test Domain Inc",
            "url": "https://example.com"
        }
        </script>
    </head>
    <body>
        <h1>Test Domain</h1>
    </body>
    </html>
    """
    orchestrator = AuditOrchestrator()
    report = orchestrator.execute_audit("https://example.com", html_override=html, status_code_override=200)

    # 1. Proves all 6 skills executed
    assert len(report.skills_run) == 6
    assert "crawl-render-audit" in report.skills_run
    assert "structured-data-audit" in report.skills_run
    assert "fact-quality-audit" in report.skills_run
    assert "freshness-corroboration" in report.skills_run
    assert "entity-identity-audit" in report.skills_run
    assert "engagement-audit" in report.skills_run

    # 2. Proves findings from skills appear in the final report
    skills_in_findings = set(f.skill for f in report.findings)
    assert "crawl-render-audit" in skills_in_findings
    assert "structured-data-audit" in skills_in_findings

    # 3. Proves summary counts match findings
    summary = report.summary
    assert summary.total_checks == len(report.findings)
    assert summary.passed == sum(1 for f in report.findings if f.status == FindingStatus.PASS)
    assert summary.failed == sum(1 for f in report.findings if f.status == FindingStatus.FAIL)
    assert summary.warnings == sum(1 for f in report.findings if f.status == FindingStatus.WARNING)
    assert summary.errors == sum(1 for f in report.findings if f.status == FindingStatus.ERROR)
    assert summary.overall_score > 0.0


def test_orchestrator_resilience_when_one_skill_fails():
    """Verify one skill crashing does not prevent remaining skills from executing or report from returning."""

    def mock_failing_skill(url, html, headers, status_code):
        raise RuntimeError("Simulated internal error in skill")

    def mock_passing_skill(url, html, headers, status_code):
        ev = Evidence(source_url=url, evidence_type="test", observed="ok")
        return [
            Finding(
                skill="working-skill",
                check_id="WK-001",
                title="Working Check",
                status=FindingStatus.PASS,
                severity=FindingSeverity.INFO,
                description="Success",
                evidence=[ev],
                recommendation="None",
            )
        ]

    custom_registry = {
        "failing-skill": mock_failing_skill,
        "working-skill": mock_passing_skill,
    }

    orchestrator = AuditOrchestrator(skill_registry=custom_registry)
    report = orchestrator.execute_audit("https://example.com", html_override="<html></html>")

    # Both skills recorded in skills_run
    assert report.skills_run == ["failing-skill", "working-skill"]

    # Findings contain the error finding from failing-skill AND the pass finding from working-skill
    assert len(report.findings) == 2

    failing_finding = next(f for f in report.findings if f.skill == "failing-skill")
    assert failing_finding.status == FindingStatus.ERROR
    assert "Simulated internal error" in failing_finding.description

    working_finding = next(f for f in report.findings if f.skill == "working-skill")
    assert working_finding.status == FindingStatus.PASS

    # Summary correctly counts 1 pass, 0 fail, 0 warning, 1 error
    assert report.summary.errors == 1
    assert report.summary.passed == 1
    assert report.summary.total_checks == 2
