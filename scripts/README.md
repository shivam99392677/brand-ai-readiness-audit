# `scripts/` — QA Fixtures & Submission Packaging

**Business logic:** two jobs that protect content quality: (1) `fixture_audit.py` — the offline content-QA harness that proves the auditor catches the four known defect classes (reach, extract, trust, engagement) with quoted evidence, using tiny local HTML servers so tests never depend on network luck; (2) `pack.py` — builds the <45 MB submission ZIP judges download.

**Tech logic:** `fixture_audit.py` serves 4 fixture site maps over `ThreadingHTTPServer` on loopback (robots.txt + homepage + interior pages), constructs `AuditOrchestrator(enable_extended_skills=True)`, runs `execute_audit`, saves `reports/fixture-<key>.json`, and prints each finding's check_id/severity/evidence/urls for human review.

```mermaid
flowchart TD
    A["python scripts/fixture_audit.py A B C D"] --> S["ThreadingHTTPServer per fixture (127.0.0.1:8801-8804)"]
    S --> B{"fixture"}
    B -->|"A: REACH"| A1["robots: 'User-agent: GPTBot / Disallow: /'"]
    B -->|"B: EXTRACT"| B1["product page, visible 49 dollars, broken JSON-LD missing closing brace"]
    B -->|"C: TRUST"| C1["/pricing $10/mo vs /docs $25/mo"]
    B -->|"D: ENGAGEMENT"| D1["H1 'Welcome', 'Learn more' href self-loop, /about/team no breadcrumbs"]
    A1 & B1 & C1 & D1 --> ORC["AuditOrchestrator(enable_extended_skills=True)"]
    ORC --> RUN["execute_audit -> reports/fixture-KEY.json"]
    RUN --> P["print check_id | severity | evidence | urls — human verdicts"]
```

### `fixture_audit.py`
**Business:** the content-QA regression harness — proves the four defect classes are caught with quoted evidence, offline and deterministically.
**Tech:** one `type()`-generated handler per fixture serves the site map (robots.txt + pages); orchestrator runs with extended skills so `CR-013`/`CR-014` are exercised; composed `report.json` per fixture is printed for human verdicts.

```mermaid
flowchart TD
    P2["python scripts/pack.py"] --> Z["build submission ZIP under 45 MB (excludes .git, venvs, caches)"]
    Z --> SUB["Adobe University Hackathon Round 3 package"]
```

### `pack.py`
**Business:** the submission artifact — judges unzip one package and run `pip install -r requirements.txt && python -m src.orchestrator …`.
**Tech:** cross-platform (Python and a `pack.sh` shell twin) ZIP builder that excludes `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and scratch report logs.

**Parent:** [repository root README](../README.md).