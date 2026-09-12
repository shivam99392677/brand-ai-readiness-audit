"""Analysis package initialization.

Exports all 6 canonical brand AI readiness audit skill functions.
"""

from src.analysis.crawl_render_audit import audit_crawl_render_skill, run_crawl_render_audit
from src.analysis.engagement_audit import EngagementAuditor, run_engagement_audit
from src.analysis.entity_identity_audit import EntityIdentityAuditor, run_entity_identity_audit
from src.analysis.fact_quality_audit import run_fact_quality_audit
from src.analysis.freshness_corroboration import FreshnessCorroborationAuditor, run_freshness_corroboration
from src.analysis.structured_data_audit import StructuredDataAuditor, audit_structured_data, run_structured_data_audit

__all__ = [
    # Canonical skill entrypoints
    "run_crawl_render_audit",
    "run_structured_data_audit",
    "run_fact_quality_audit",
    "run_freshness_corroboration",
    "run_entity_identity_audit",
    "run_engagement_audit",
    # Backward compatibility helpers & auditors
    "audit_crawl_render_skill",
    "audit_structured_data",
    "StructuredDataAuditor",
    "FreshnessCorroborationAuditor",
    "EntityIdentityAuditor",
    "EngagementAuditor",
]
