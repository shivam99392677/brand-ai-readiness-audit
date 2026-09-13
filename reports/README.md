# `reports/` — Audit Outputs & Content-QA Records

**Business logic:** this folder holds the evidence trail of the Round-3 content review: real-site `report.json` outputs (before/after fixes), the fixture reports proving every defect class is caught, and the run logs. It is intentionally committed so evaluators can diff the before/after finding lists (e.g. example.com dropping from HIGH/medium false defects to 5 LOW truths).

**Tech logic:** files named `<host>.json` (live audits), `example.com.after.json` / `mozilla.after.json` (post-fix re-runs), `fixture-{A,B,C,D}.json` (offline content-QA runs from `scripts/fixture_audit.py`), and `.log` files from the orchestrator CLI runs.

```mermaid
flowchart TD
    LIVE["python -m src.orchestrator <host> -o reports/<host>.json"] --> LIVEJ["live reports:<br/>example.com, wikipedia.org, docs.python.org,<br/>stripe.com, mozilla.org, python.org, news.ycombinator.com"]
    FIX["python scripts/fixture_audit.py A B C D"] --> FIXJ["fixture-A.json: GPTBot blocked (HIGH CR-014)<br/>fixture-B.json: broken JSON-LD (HIGH SD-002)<br/>fixture-C.json: price contradiction (HIGH FQ-02)<br/>fixture-D.json: EG-01 + EG-04 + EG-03"]
    AFTER["post-fix re-runs"] --> AFTERJ["example.com.after.json: 0 high / 0 medium / 5 low<br/>mozilla.after.json: timeouts demoted to LOW not-scored"]
    LIVEJ & FIXJ & AFTERJ --> QA["content QA: verdict cards + precision + before/after"]
```

**Parent:** [repository root README](../README.md).