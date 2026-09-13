#!/usr/bin/env python3
"""CLI wrapper for the crawl-render-audit specialist skill."""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "reason": "usage: python scripts/run.py <manifest.json>"}))
        sys.exit(0)

    manifest_path = sys.argv[1]
    try:
        from src.crawler.engine import CrawlManifest
        from src.extraction.extraction_manager import ExtractionManager
        from src.analysis.crawl_render_audit import run_crawl_render_audit

        with open(manifest_path, encoding="utf-8") as fh:
            data = json.load(fh)
        crawl = data.get("crawl") if isinstance(data, dict) and "crawl" in data else data
        manifest = CrawlManifest.model_validate(crawl)
        evidence = ExtractionManager().extract(manifest)
        website = manifest.website_evidence
        findings = run_crawl_render_audit(evidence=evidence, website=website)
        print(json.dumps(
            {"ok": True, "skill": "crawl-render-audit", "findings": [f.model_dump() for f in findings]},
            default=str, indent=2
        ))
    except Exception as err:
        print(json.dumps(
            {"ok": False, "reason": f"cannot build evidence store ({type(err).__name__}): {err} - skipped"}
        ))
    sys.exit(0)
