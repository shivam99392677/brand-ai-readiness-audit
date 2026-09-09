"""Evidence Extraction Package for Brand AI Readiness Audit.

Exports modular extractors, ExtractionManager, deterministic ID generator,
and legacy extraction helper functions.
"""

from src.extraction.entity_extractor import EntityExtractor
from src.extraction.extraction_manager import ExtractionManager
from src.extraction.freshness_extractor import FreshnessExtractor
from src.extraction.http_extractor import HTTPExtractor
from src.extraction.id_generator import EvidenceIdGenerator
from src.extraction.images import extract_page_images
from src.extraction.link_extractor import LinkExtractor
from src.extraction.links import extract_page_links_and_resources
from src.extraction.media_extractor import MediaExtractor
from src.extraction.metadata import extract_page_metadata
from src.extraction.metadata_extractor import MetadataExtractor
from src.extraction.page import extract_page_content
from src.extraction.resource_extractor import ResourceExtractor
from src.extraction.robots_extractor import RobotsExtractor
from src.extraction.schema_extractor import SchemaExtractor
from src.extraction.site_extractor import SiteExtractor
from src.extraction.structured_data import extract_schema_objects, extract_structured_data, get_type_names
from src.extraction.text_extractor import TextExtractor

__all__ = [
    # Master Manager & Generator
    "ExtractionManager",
    "EvidenceIdGenerator",
    # Modular Extractors
    "HTTPExtractor",
    "TextExtractor",
    "MetadataExtractor",
    "SchemaExtractor",
    "RobotsExtractor",
    "FreshnessExtractor",
    "EntityExtractor",
    "LinkExtractor",
    "MediaExtractor",
    "ResourceExtractor",
    "SiteExtractor",
    # Helper / Legacy Extraction Functions
    "extract_page_metadata",
    "extract_page_content",
    "extract_page_images",
    "extract_page_links_and_resources",
    "extract_structured_data",
    "extract_schema_objects",
    "get_type_names",
]
