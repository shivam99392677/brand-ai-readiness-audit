"""Shared Evidence Package."""

from src.evidence.models import (
    ContactEvidence,
    DateEvidence,
    DocumentEvidence,
    FormEvidence,
    FormInputField,
    ImageEvidence,
    LinkEvidence,
    PageEvidence,
    PageRoleSignals,
    Provenance,
    RobotsEvidence,
    SitemapEvidence,
    UserAgentRuleGroup,
    WebsiteEvidence,
)
from src.shared.evidence_schema import (
    CanonicalEvidence,
    EvidenceType,
    ExtractionError,
    ExtractionResult,
)

__all__ = [
    "Provenance",
    "CanonicalEvidence",
    "EvidenceType",
    "ExtractionError",
    "ExtractionResult",
    "UserAgentRuleGroup",
    "RobotsEvidence",
    "SitemapEvidence",
    "ImageEvidence",
    "LinkEvidence",
    "FormInputField",
    "FormEvidence",
    "DocumentEvidence",
    "ContactEvidence",
    "DateEvidence",
    "PageRoleSignals",
    "PageEvidence",
    "WebsiteEvidence",
]
