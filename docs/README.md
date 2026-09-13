# `docs/` — Design Documentation

**Business logic:** the written reasoning a judge reads to understand *why* the audit measures what it measures: the observation→finding→severity→recommendation evidence model, the full audit matrix (every check id with severity and false-positive notes), architecture decisions, and Round-3 research.

**Tech logic:** four markdown documents mirroring the implementation:

```mermaid
flowchart TD
    M1["audit-matrix.md<br/>observation/evidence -> finding -> severity -> recommendation;<br/>full check tables CR/SD/FQ/FC/EI/EG + false-positive considerations"] --> IMP["mirrors src/analysis/*"]
    M2["architecture.md<br/>crawl -> extraction -> 6 skills -> composer;<br/>canonical evidence schema (EV ids, provenance)"] --> IMP2["mirrors src/crawler + src/extraction + src/shared"]
    M3["decisions.md<br/>Round-3 content-QA decisions (severity demotions,<br/>scope rules, check implementations)"] --> IMP3["mirrors git history of fixes"]
    M4["research.md<br/>AI discoverability / freshness / engagement research"] --> IMP4["grounds severity choices"]
    IMP & IMP2 & IMP3 & IMP4 --> J["judge context"]
```

| File | Reads best for |
|---|---|
| `audit-matrix.md` | every check id, severity, and false-positive consideration (e.g. EG skill scope note excluding llms.txt/OpenAPI/chatbot) |
| `architecture.md` | pipeline flow, evidence schema, component responsibilities |
| `decisions.md` | the content-QA verdicts and their fixes from Round 3 |
| `research.md` | background research on AI discoverability, freshness, engagement |

**Parent:** [repository root README](../README.md).