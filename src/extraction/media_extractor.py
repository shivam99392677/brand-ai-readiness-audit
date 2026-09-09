"""Media and Form Evidence Extractor.

Extracts image asset properties (dimensions, alt text, captions, formats, tracking filters)
and interactive HTML form structures (actions, methods, inputs, buttons).
This module is strictly factual and does NOT evaluate image quality or form readiness.
"""

from typing import Any, Dict, List, Optional
from src.evidence.models import FormEvidence, ImageEvidence
from src.extraction.images import extract_page_images
from src.extraction.links import extract_page_links_and_resources
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance


class MediaExtractor:
    """Extracts factual image asset signals and interactive form elements."""

    def extract_media_evidence(
        self,
        url: str,
        html_content: Optional[str] = None,
        images: Optional[List[ImageEvidence]] = None,
        forms: Optional[List[FormEvidence]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized image and form evidence items."""
        evidence_items: List[CanonicalEvidence] = []
        has_raw_html = bool(html_content and html_content.strip())

        extracted_images: List[ImageEvidence] = []
        extracted_forms: List[FormEvidence] = []

        if has_raw_html:
            extracted_images = extract_page_images(html_content, url=url)
            res = extract_page_links_and_resources(html_content, url=url)
            extracted_forms = res["forms"]
            source_desc = "raw_html"
            method_desc = "html-parser"
        else:
            extracted_images = images or []
            extracted_forms = forms or []
            source_desc = "crawler.page_evidence"
            method_desc = "direct-field"

        # 1. Image Asset Evidence
        for idx, img in enumerate(extracted_images):
            img_data = {
                "declared_url": img.declared_url,
                "resolved_url": img.resolved_url or img.url,
                "source_page": url,
                "source_type": img.source_type,
                "alt": img.alt,
                "title": img.title,
                "declared_width": img.declared_width,
                "declared_height": img.declared_height,
                "intrinsic_width": img.intrinsic_width,
                "intrinsic_height": img.intrinsic_height,
                "srcset": img.srcset,
                "loading": img.loading,
                "format": img.format,
                "caption": img.caption,
                "linked_href": img.linked_href,
                "is_tracking_or_icon": img.is_tracking_or_icon,
                "filter_reason": img.filter_reason,
                "order_index": idx,
            }
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.IMAGE_ITEM,
                    source="html_body",
                    url=url,
                    data=img_data,
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<img src='{img.declared_url[:60]}'>",
                        context=img.alt or img.caption,
                    ),
                )
            )

        # 2. Interactive Form Evidence
        for f_idx, form in enumerate(extracted_forms):
            inputs_data = [
                {
                    "input_type": inp.input_type,
                    "name": inp.name,
                    "id": inp.id,
                    "label": inp.label,
                    "placeholder": inp.placeholder,
                }
                for inp in form.inputs
            ]
            form_data = {
                "source_page": url,
                "action": form.action,
                "method": form.method.lower(),
                "inputs": inputs_data,
                "inputs_count": len(inputs_data),
                "buttons": form.buttons,
                "order_index": f_idx,
            }
            evidence_items.append(
                CanonicalEvidence(
                    id="",
                    type=EvidenceType.FORM_ITEM,
                    source="html_body",
                    url=url,
                    data=form_data,
                    provenance=Provenance(
                        source=source_desc,
                        extraction_method=method_desc,
                        url=url,
                        location=f"<form action='{(form.action or '')[:60]}'>",
                    ),
                )
            )

        return evidence_items
