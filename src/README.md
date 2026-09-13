# `src/` — Core Package

**Business logic:** this package *is* the product. A brand team points it at one URL and receives an evidence-backed report of every defect that would make their site hard for AI assistants (ChatGPT, Perplexity, Gemini) to crawl, read, extract, trust, or convert visitors on. Every finding must quote real page data — a report sentence a human cannot re-verify on the live page is treated as a bug.

**Tech logic:** strict one-directional pipeline. The orchestrator crawls, the extraction layer converts raw HTTP/DOM data into canonical evidence objects, six analysis skills evaluate evidence into findings, and the composer serializes findings into the Adobe Hackathon JSON schema. No skill talks to the network about another skill's data — evidence flows one way.

```mermaid
flowchart TD
    A["src/orchestrator.py<br/>AuditOrchestrator: CLI entry, crawl + dispatch"] --> B["src/crawler/<br/>SiteCrawler: robots, sitemap, fetch, render"]
    B --> C["src/extraction/<br/>ExtractionManager: HTML → CanonicalEvidence"]
    C --> D["src/shared/evidence_schema.py<br/>EvidenceType + Provenance contract"]
    D --> E["src/analysis/<br/>6 core + 2 extended audit skills"]
    E --> F["src/models.py<br/>Finding + Evidence + score math"]
    E --> G["src/reporting/composer.py<br/>Adobe report.json serializer"]
    F --> G
```

## Files in this directory

| File | Role | Own diagram |
|---|---|---|
| `orchestrator.py` | Master entrypoint: validates URL, crawls, runs skill registry, saves report | [below](#orchestratorpy) |
| `models.py` | `Evidence`, `Finding`, `AuditSummary`, `AuditReport` + deterministic score | [below](#modelspy) |
| `__init__.py` | Package marker (exposes `src` as an importable package for `python -m src.orchestrator`) | — |

<a id="orchestratorpy"></a>
### `orchestrator.py`

**Business:** the single command a judge or brand manager runs. Must produce a truthful `report.json` for any URL with bounded cost (`--max-pages`, `--max-depth`).
**Tech:** `validate_target_url()` → `SiteCrawler.crawl_site()` → `ExtractionManager.extract()` → iterate `CORE_SKILL_REGISTRY` (6 skills, always on) + optional `EXTENDED_SKILL_REGISTRY` (sitemap-audit, bot-block-audit) → `AdobeReportComposer` → JSON file. Supports `html_override` / `custom_fetcher` so tests can run with zero network.

```mermaid
flowchart TD
    U["CLI: python -m src.orchestrator URL --max-pages N --max-depth D -o out.json"] --> V["validate_target_url()"]
    V --> CR["crawl_site() -> CrawlManifest"]
    CR --> EX["ExtractionManager.extract() -> ExtractionResult"]
    EX --> REG{"skill registry"}
    REG -->|"core, always"| S1["crawl-render, structured-data, fact-quality"]
    REG -->|"core, always"| S2["freshness, entity-identity, engagement"]
    REG -->|"enable_extended_skills=True"| S3["sitemap-audit, bot-block-audit"]
    S1 & S2 & S3 --> CMP["AdobeReportComposer.compose()"]
    CMP --> OUT["report.json (F-001..F-NNN, evidence strings)"]
```

<a id="modelspy"></a>
### `models.py`

**Business:** the shared language of the audit. A finding is only publishable if it has non-empty evidence, a severity, and an actionable recommendation — the validators refuse anything less, which is what keeps marketing fluff out of `findings[]`.
**Tech:** Pydantic models with `field_validator` guards; `calculate_summary()` computes a 0–100 readiness score by severity weights (CRITICAL 2.0 … INFO 0.2), counting PASS as full weight and WARNING as half; any CRITICAL fail caps the score at 40.

```mermaid
flowchart TD
    F0["Finding created by a skill"] --> V1{"validators:<br/>skill/check_id/title/description/recommendation non-empty?"}
    V1 -->|"no"| X["ValidationError — finding cannot exist"]
    V1 -->|"yes"| V2{"evidence list of Evidence<br/>(source_url, observed != None)?"}
    V2 -->|"no"| X
    V2 -->|"yes"| S["calculate_summary()"]
    S --> W["weight per severity:<br/>CRIT 2.0 / HIGH 1.5 / MED 1.0 / LOW 0.5 / INFO 0.2"]
    W --> P{"status?"}
    P -->|PASS| F1["add full weight"]
    P -->|WARNING| F2["add half weight"]
    P -->|FAIL| F3["add 0"]
    F1 & F2 & F3 --> SC["score = earned/possible * 100"]
    SC --> CAP{"any CRITICAL fail?"}
    CAP -->|"yes"| C40["cap score at 40"]
    CAP -->|"no"| R["round 0-100 -> AuditReport.summary"]
```

**Parent:** see [repository map in the root README](../README.md).