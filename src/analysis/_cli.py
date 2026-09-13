"""Shared standalone CLI for the specialist audit modules.

Used by Agent Skills:  python src/analysis/<skill>.py <manifest.json>

<manifest.json> is a CrawlManifest dump (the 'crawl' field of an Adobe
report.json, or a full AuditReport JSON). This helper rebuilds the
canonical evidence store and runs the requested specialist. If the store
cannot be loaded it SKIPS (prints ok:false) rather than fabricating
findings — specialists never crawl and never invent results.
"""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # src/analysis -> repository root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_specialist(module_name: str, fn_name: str) -> int:
    if len(sys.argv) < 2:
        print(json.dumps({
            "ok": False,
            "reason": f"usage: python src/analysis/{module_name}.py <manifest.json>",
        }))
        return 0

    manifest_path = sys.argv[1]
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            data = json.load(fh)
        crawl = data.get("crawl") if isinstance(data, dict) and "crawl" in data else data

        from src.crawler.engine import CrawlManifest
        from src.extraction.extraction_manager import ExtractionManager

        manifest = CrawlManifest.model_validate(crawl)
        evidence = ExtractionManager().extract(manifest)
        website = manifest.website_evidence

        mod = importlib.import_module(f"src.analysis.{module_name}")
        findings = getattr(mod, fn_name)(evidence=evidence, website=website)

        print(json.dumps({
            "ok": True,
            "skill": module_name,
            "findings": [f.model_dump() for f in findings],
        }, default=str, indent=2))
    except Exception as err:  # noqa: BLE001 - specialists skip instead of crashing
        print(json.dumps({
            "ok": False,
            "reason": f"cannot build the entrypoint evidence store ({type(err).__name__}): "
                      f"{err} — skipped, do not invent findings",
        }))
    return 0