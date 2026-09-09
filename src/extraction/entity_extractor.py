"""Entity Identity Evidence Extractor.

Extracts factual organization names, addresses, phone numbers, email addresses,
logo assets, sameAs cross-references, social profile links, and Wikidata entity IDs.
This module does NOT evaluate identity consistency or NAP uniformity.
"""

import re
from typing import Any, Dict, List, Optional
from src.evidence.models import ContactEvidence
from src.extraction.structured_data import extract_schema_objects, get_type_names
from src.shared.evidence_schema import CanonicalEvidence, EvidenceType, Provenance

SOCIAL_DOMAINS = [
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "github.com",
    "tiktok.com",
]


class EntityExtractor:
    """Extracts factual entity signals from JSON-LD, metadata, links, and contact text."""

    def extract_entity_evidence(
        self,
        url: str,
        jsonld_objects: Optional[List[Dict[str, Any]]] = None,
        contacts: Optional[ContactEvidence] = None,
        meta_tags: Optional[List[Dict[str, str]]] = None,
        links: Optional[List[Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Extracts normalized entity identity evidence items."""
        evidence_items: List[CanonicalEvidence] = []

        # 1. Extract from JSON-LD Objects
        if jsonld_objects:
            for b_idx, block in enumerate(jsonld_objects):
                schemas = extract_schema_objects(block)
                for s_idx, s in enumerate(schemas):
                    types = [t.lower() for t in get_type_names(s.get("@type") or s.get("type"))]

                    # Organization, LocalBusiness, Corporation, Brand, Person
                    is_entity_type = any(
                        t in ("organization", "localbusiness", "corporation", "brand", "person", "collegeoruniversity", "educationalorganization")
                        for t in types
                    )

                    # Extract Name
                    name_val = s.get("name") or s.get("legalName") or s.get("alternateName")
                    if name_val and isinstance(name_val, str) and name_val.strip():
                        evidence_items.append(
                            CanonicalEvidence(
                                id="",
                                type=EvidenceType.ENTITY_NAME,
                                source="json_ld",
                                url=url,
                                data={
                                    "name": name_val.strip(),
                                    "field": "name" if "name" in s else ("legalName" if "legalName" in s else "alternateName"),
                                    "schema_type": types[0] if types else "Organization",
                                },
                                provenance=Provenance(
                                    source="jsonld_parsed",
                                    extraction_method="schema-property",
                                    url=url,
                                    location=f"JSON-LD:{types[0] if types else 'Entity'}:name",
                                    path=f"$[block_{b_idx}][{s_idx}].name",
                                ),
                            )
                        )

                    # Extract Logo
                    logo_val = s.get("logo") or s.get("image")
                    if logo_val:
                        logo_url = logo_val if isinstance(logo_val, str) else (logo_val.get("url") if isinstance(logo_val, dict) else None)
                        if logo_url and isinstance(logo_url, str):
                            evidence_items.append(
                                CanonicalEvidence(
                                    id="",
                                    type=EvidenceType.ENTITY_LOGO,
                                    source="json_ld",
                                    url=url,
                                    data={"logo_url": logo_url.strip(), "schema_type": types[0] if types else "Organization"},
                                    provenance=Provenance(
                                        source="jsonld_parsed",
                                        extraction_method="schema-property",
                                        url=url,
                                        location=f"JSON-LD:{types[0] if types else 'Entity'}:logo",
                                    ),
                                )
                            )

                    # Extract sameAs links & Wikidata
                    same_as = s.get("sameAs")
                    same_as_list: List[str] = []
                    if isinstance(same_as, str) and same_as.strip():
                        same_as_list = [same_as.strip()]
                    elif isinstance(same_as, list):
                        same_as_list = [str(item).strip() for item in same_as if isinstance(item, str) and item.strip()]

                    for sa_url in same_as_list:
                        evidence_items.append(
                            CanonicalEvidence(
                                id="",
                                type=EvidenceType.SAME_AS_LINK,
                                source="json_ld",
                                url=url,
                                data={"same_as_url": sa_url, "schema_type": types[0] if types else "Organization"},
                                provenance=Provenance(
                                    source="jsonld_parsed",
                                    extraction_method="schema-property",
                                    url=url,
                                    location=f"JSON-LD:sameAs",
                                ),
                            )
                        )
                        if "wikidata.org" in sa_url.lower():
                            wiki_match = re.search(r"Q\d+", sa_url)
                            evidence_items.append(
                                CanonicalEvidence(
                                    id="",
                                    type=EvidenceType.WIKIDATA_ID,
                                    source="json_ld",
                                    url=url,
                                    data={
                                        "wikidata_url": sa_url,
                                        "wikidata_id": wiki_match.group(0) if wiki_match else None,
                                    },
                                    provenance=Provenance(
                                        source="jsonld_parsed",
                                        extraction_method="wikidata-url-parse",
                                        url=url,
                                        location=f"JSON-LD:sameAs > wikidata",
                                    ),
                                )
                            )

                    # Extract Address from Schema
                    addr = s.get("address")
                    if addr:
                        addr_str = addr if isinstance(addr, str) else (
                            f"{addr.get('streetAddress', '')} {addr.get('addressLocality', '')} {addr.get('addressRegion', '')} {addr.get('postalCode', '')} {addr.get('addressCountry', '')}".strip()
                            if isinstance(addr, dict) else str(addr)
                        )
                        if addr_str:
                            evidence_items.append(
                                CanonicalEvidence(
                                    id="",
                                    type=EvidenceType.ENTITY_ADDRESS,
                                    source="json_ld",
                                    url=url,
                                    data={"address": addr_str, "structured_address": addr if isinstance(addr, dict) else None},
                                    provenance=Provenance(
                                        source="jsonld_parsed",
                                        extraction_method="schema-property",
                                        url=url,
                                        location="JSON-LD:address",
                                    ),
                                )
                            )

                    # Extract Telephone from Schema
                    tel = s.get("telephone")
                    if tel and isinstance(tel, str) and tel.strip():
                        evidence_items.append(
                            CanonicalEvidence(
                                id="",
                                type=EvidenceType.ENTITY_PHONE,
                                source="json_ld",
                                url=url,
                                data={"phone": tel.strip(), "source": "jsonld"},
                                provenance=Provenance(
                                    source="jsonld_parsed",
                                    extraction_method="schema-property",
                                    url=url,
                                    location="JSON-LD:telephone",
                                ),
                            )
                        )

                    # Extract Email from Schema
                    email_prop = s.get("email")
                    if email_prop and isinstance(email_prop, str) and email_prop.strip():
                        evidence_items.append(
                            CanonicalEvidence(
                                id="",
                                type=EvidenceType.ENTITY_EMAIL,
                                source="json_ld",
                                url=url,
                                data={"email": email_prop.strip(), "source": "jsonld"},
                                provenance=Provenance(
                                    source="jsonld_parsed",
                                    extraction_method="schema-property",
                                    url=url,
                                    location="JSON-LD:email",
                                ),
                            )
                        )

        # 2. Extract from Contact Signals (DOM Text)
        if contacts:
            for email_str in contacts.emails:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.ENTITY_EMAIL,
                        source="html_body",
                        url=url,
                        data={"email": email_str, "source": "dom_text"},
                        provenance=Provenance(
                            source="raw_html",
                            extraction_method="regex-search",
                            url=url,
                            location="<body> > text()",
                            context=f"email:{email_str}",
                        ),
                    )
                )

            for phone_str in contacts.phone_numbers:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.ENTITY_PHONE,
                        source="html_body",
                        url=url,
                        data={"phone": phone_str, "source": "dom_text"},
                        provenance=Provenance(
                            source="raw_html",
                            extraction_method="regex-search",
                            url=url,
                            location="<body> > text()",
                            context=f"phone:{phone_str}",
                        ),
                    )
                )

            for addr_str in contacts.addresses:
                evidence_items.append(
                    CanonicalEvidence(
                        id="",
                        type=EvidenceType.ENTITY_ADDRESS,
                        source="html_body",
                        url=url,
                        data={"address": addr_str, "source": "dom_text"},
                        provenance=Provenance(
                            source="raw_html",
                            extraction_method="regex-search",
                            url=url,
                            location="<body> > text()",
                            context=addr_str,
                        ),
                    )
                )

        # 3. Extract Social Links from Anchor Links
        if links:
            for link in links:
                target_href = link.href if hasattr(link, "href") else (link.get("href") if isinstance(link, dict) else "")
                if target_href:
                    target_lower = target_href.lower()
                    for s_domain in SOCIAL_DOMAINS:
                        if s_domain in target_lower:
                            evidence_items.append(
                                CanonicalEvidence(
                                    id="",
                                    type=EvidenceType.SAME_AS_LINK,
                                    source="html_body",
                                    url=url,
                                    data={"same_as_url": target_href, "network": s_domain.split(".")[0]},
                                    provenance=Provenance(
                                        source="raw_html",
                                        extraction_method="link-inspection",
                                        url=url,
                                        location=f"<a href='{target_href[:60]}'>",
                                    ),
                                )
                            )

        return evidence_items
