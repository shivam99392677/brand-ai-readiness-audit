"""Unit tests for src/analysis/structured_data_audit.py."""

import pytest
from src.analysis.structured_data_audit import StructuredDataAuditor, audit_structured_data
from src.models import FindingStatus, FindingSeverity


def test_valid_json_ld():
    """Test auditing HTML with a valid Organization JSON-LD script block."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Acme Corporation - Official Site</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Acme Corporation",
            "url": "https://example.com"
        }
        </script>
    </head>
    <body>
        <h1>Acme Corporation</h1>
    </body>
    </html>
    """
    findings = audit_structured_data(html, "https://example.com")
    finding_map = {f.check_id: f for f in findings}

    assert len(findings) == 6

    # SD-001 JSON-LD Detection
    assert finding_map["SD-001"].status == FindingStatus.PASS
    assert finding_map["SD-001"].evidence[0].observed["detected_count"] == 1

    # SD-002 JSON-LD Parse Validity
    assert finding_map["SD-002"].status == FindingStatus.PASS
    assert finding_map["SD-002"].evidence[0].observed["valid_blocks"] == 1

    # SD-003 Schema Type Detection
    assert finding_map["SD-003"].status == FindingStatus.PASS
    assert "Organization" in finding_map["SD-003"].evidence[0].observed["detected_schema_types"]

    # SD-004 Entity Information Completeness
    assert finding_map["SD-004"].status == FindingStatus.PASS

    # SD-005 Visible Content Consistency
    assert finding_map["SD-005"].status == FindingStatus.PASS

    # SD-006 Duplicate / Conflicting Data
    assert finding_map["SD-006"].status == FindingStatus.PASS


def test_malformed_json_ld():
    """Test auditing HTML with a syntax error in JSON-LD."""
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Broken JSON",
        }
        </script>
    </head>
    </html>
    """
    auditor = StructuredDataAuditor(html, "https://example.com")
    findings = auditor.run_all_checks()
    finding_map = {f.check_id: f for f in findings}

    # SD-001 Detection passes
    assert finding_map["SD-001"].status == FindingStatus.PASS

    # SD-002 Validity fails due to trailing comma
    assert finding_map["SD-002"].status == FindingStatus.FAIL
    assert finding_map["SD-002"].severity == FindingSeverity.HIGH
    assert "parse_error" in finding_map["SD-002"].evidence[0].observed


def test_multiple_json_ld_blocks_and_conflicts():
    """Test auditing HTML with multiple JSON-LD script blocks containing conflicting entity names."""
    html = """
    <html>
    <head>
        <title>Brand Portal</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Alpha Brand",
            "url": "https://example.com"
        }
        </script>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Beta Brand",
            "url": "https://example.com"
        }
        </script>
    </head>
    </html>
    """
    findings = audit_structured_data(html, "https://example.com")
    finding_map = {f.check_id: f for f in findings}

    # SD-001: 2 blocks detected
    assert finding_map["SD-001"].status == FindingStatus.PASS
    assert finding_map["SD-001"].evidence[0].observed["detected_count"] == 2

    # SD-002: Both parse validly
    assert finding_map["SD-002"].status == FindingStatus.PASS

    # SD-006: Duplicate conflicting entity names detected
    assert finding_map["SD-006"].status == FindingStatus.FAIL
    assert "Organization" in finding_map["SD-006"].evidence[0].observed["conflicting_types"]


def test_missing_json_ld():
    """Test auditing HTML with no JSON-LD script blocks."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Plain Page</title>
        <meta property="og:title" content="Plain Page Title" />
    </head>
    <body>
        <h1>Welcome</h1>
    </body>
    </html>
    """
    findings = audit_structured_data(html, "https://example.com")
    finding_map = {f.check_id: f for f in findings}

    # SD-001: Missing schema on plain page is NOT_APPLICABLE (not a defect)
    assert finding_map["SD-001"].status == FindingStatus.NOT_APPLICABLE

    # SD-002: Not applicable
    assert finding_map["SD-002"].status == FindingStatus.NOT_APPLICABLE

    # SD-004: Not applicable
    assert finding_map["SD-004"].status == FindingStatus.NOT_APPLICABLE


def test_visible_consistency_conflict():
    """Test SD-005 when structured data entity name conflicts with visible title/H1."""
    html = """
    <html>
    <head>
        <title>Gizmo Widget Store</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Super Dooper Quantum Leap Device"
        }
        </script>
    </head>
    <body>
        <h1>Gizmo Widget Store</h1>
    </body>
    </html>
    """
    findings = audit_structured_data(html, "https://example.com")
    finding_map = {f.check_id: f for f in findings}

    # SD-005: Discrepancy between "Super Dooper Quantum..." and "Gizmo Widget Store"
    assert finding_map["SD-005"].status == FindingStatus.FAIL
    assert finding_map["SD-005"].severity == FindingSeverity.HIGH
