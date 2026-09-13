"""STEP C live-battery validator.

Asserts for each saved live report:
  - required keys: site, audited_at, summary, findings
  - suggested_action is an object with priority in {high, medium, low}
  - NO finding title contains llms.txt / OpenAPI / chatbot
  - every finding evidence mentions a URL or a count
  - example.com: no missing-schema defect; no medium missing-sameAs
  - wikipedia vs docs.python.org finding sets DIFFER (anti-overfit)

Run: python tests/validate_live_samples.py
"""

import json
import os
import re
import sys

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "live-samples")
FORBIDDEN = ("llms.txt", "openapi", "chatbot", "chat widget")


def load(name):
    path = os.path.join(SAMPLES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_common(rep, label):
    errors = []
    for key in ("site", "audited_at", "summary", "findings"):
        if key not in rep:
            errors.append(f"{label}: missing key '{key}'")
    if not re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", rep.get("audited_at", "")):
        errors.append(f"{label}: audited_at not ISO-8601Z: {rep.get('audited_at')}")
    for i, f in enumerate(rep.get("findings", []), 1):
        sa = f.get("suggested_action")
        if not isinstance(sa, dict):
            errors.append(f"{label} F-{i:03d}: suggested_action not an object")
        elif sa.get("priority") not in ("high", "medium", "low"):
            errors.append(f"{label} F-{i:03d}: bad priority {sa.get('priority')!r}")
        title = (f.get("title") or "").lower()
        if any(tok in title for tok in FORBIDDEN):
            errors.append(f"{label} F-{i:03d}: forbidden title: {f.get('title')}")
        ev = (f.get("evidence") or "")
        has_url = "http" in ev or "/" in ev
        has_count = bool(re.search(r"\d", ev))
        if not (has_url or has_count):
            errors.append(f"{label} F-{i:03d}: evidence lacks URL or count: {ev[:80]}")
    return errors


def main():
    all_errors = []

    example = load("example.json")
    wiki = load("wikipedia.json")
    docs = load("docs-python.json")

    for rep, label in ((example, "example.com"), (wiki, "wikipedia"), (docs, "docs.python.org")):
        all_errors.extend(validate_common(rep, label))

    # example.com specific: no missing-schema defect, no medium missing-sameAs
    for f in example.get("findings", []):
        title = (f.get("title") or "").lower()
        if "schema" in title and f.get("severity") in ("high", "critical", "medium"):
            all_errors.append(f"example.com: missing-schema defect present: {f.get('title')}")
        if "sameas" in title and f.get("severity") == "medium":
            all_errors.append(f"example.com: medium missing-sameAs present: {f.get('title')}")

    # Anti-overfit: wikipedia vs docs.python.org finding sets must differ
    wiki_ids = sorted(f.get("check_id", f.get("id")) for f in wiki.get("findings", []))
    docs_ids = sorted(f.get("check_id", f.get("id")) for f in docs.get("findings", []))
    if wiki_ids == docs_ids:
        all_errors.append("anti-overfit: wikipedia and docs.python.org finding sets are identical")

    print("=== Live battery validation ===")
    print(f"example.com     : {example['summary']['total_findings']} findings "
          f"(ids: {[f['check_id'] for f in example['findings']]})")
    print(f"wikipedia       : {wiki['summary']['total_findings']} findings "
          f"(ids: {[f['check_id'] for f in wiki['findings']]})")
    print(f"docs.python.org : {docs['summary']['total_findings']} findings "
          f"(ids: {[f['check_id'] for f in docs['findings']]})")

    if all_errors:
        print("\nFAILURES:")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    print("\nALL LIVE-BATTERY ASSERTIONS PASSED")


if __name__ == "__main__":
    main()