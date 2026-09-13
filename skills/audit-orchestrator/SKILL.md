---
name: audit-orchestrator
description: >
  Entrypoint skill that runs a full AI-discoverability + on-site engagement
  audit of a brand website and returns the canonical Adobe report.json.
  Use when asked to "audit this site for AI discoverability", "check if
  assistants can find/cite this brand", "run a brand AI readiness audit", or
  "audit website engagement". This is the only skill to start with — it
  orchestrates all 6 specialist skills automatically.
license: MIT
allowed-tools: GET HTTP, read files, run bundled Python scripts
---

## When to use
Use this skill when asked to audit a website for AI discoverability (why
assistants don't find or cite it) and on-site engagement (why visitors don't
stay). Trigger phrases: "audit this site", "AI discoverability audit",
"brand AI readiness", "website audit for AI", "check if my site is AI-ready".

This is the ONLY skill you should start with. The 6 specialist skills are
invoked automatically by this orchestrator — do not invoke them directly.

## Inputs
- URL or domain to audit (e.g. `https://example.com`)
- Optional: `--max-pages N` (default 100), `--max-depth N` (default 3),
  `-o report.json` (output path, default `report.json`)

## Procedure
Execute these steps in order. Do not skip steps.

1. **Validate the URL.** It must start with `http://` or `https://` and have
   a non-empty hostname. If invalid, stop and report the error.

2. **Run the bundled script.** Do not figure out Python imports or crawl the
   site yourself. Run exactly:
   ```bash
   python {baseDir}/scripts/run.py <URL> -o report.json
   ```
   where `{baseDir}` is this skill's folder (`skills/audit-orchestrator/`).
   Equivalently, from the marketplace root:
   ```bash
   python skills/audit-orchestrator/scripts/run.py https://example.com -o report.json
   ```
   The script crawls the site, extracts evidence, runs all 6 specialist audits,
   and writes `report.json`. Default limits: 100 pages, depth 3. For a quick
   check use `--max-pages 8 --max-depth 1`.

3. **Read report.json.** Parse the JSON file the script wrote.

4. **Return it unchanged.** Return the exact contents of `report.json` as the
   skill result. Do not rewrite, filter, re-rank, or summarize the findings.
   The report is the output.

## Output
A single Adobe report JSON file (`report.json`). See `references/checks.md`
for the check list and `src/README.md` for the engine design.

Minimal schema:
```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3 },
  "findings": [
    {
      "id": "F-001",
      "title": "...",
      "severity": "high",
      "evidence": "URL + count or quoted snippet a non-expert can re-find.",
      "suggested_action": { "summary": "...", "priority": "high" }
    }
  ]
}
```
`severity` is one of `critical`, `high`, `medium`, `low`. `suggested_action` is
an object with `summary` and `priority` (never a string).

## Allowed tools
- GET HTTP requests (to the target site and public corroboration sources)
- Read local files (the report, the SKILL.md, references/)
- Run the bundled Python script (`scripts/run.py`)
- Write only the output report file (`report.json`)

NO writes to the target site. NO POST/PUT/PATCH/DELETE. NO browser automation
(Playwright) unless the script explicitly decides to render — the script owns
that decision, not the agent.
