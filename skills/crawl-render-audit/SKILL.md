---
name: crawl-render-audit
description: >
  Audits whether a website's pages are reachable and readable by AI crawlers:
  HTTP status, robots.txt / X-Robots-Tag directives, text extractability,
  heading structure, internal links, and SSR/CSR parity. Use when the
  entrypoint report flags "pages are empty JS shells", "robots.txt blocks AI
  bots", or "text not extractable". Do NOT start here.
license: MIT
allowed-tools: GET HTTP, parse HTML, read files, run bundled Python scripts
---

## When to use
This skill evaluates technical accessibility and text extractability of web
pages for AI crawlers. Trigger phrases: "crawl audit", "robots.txt check",
"JS shell audit", "text extractability", "SSR CSR parity".

**Do not start here.** This is a specialist skill invoked automatically by the
entrypoint (audit-orchestrator). If you are auditing a site, start with the
entrypoint skill. Only invoke this skill directly if:
- You already have a report.json or crawl manifest from the entrypoint, AND
- You need to re-run or inspect only the crawl/render findings.

## Inputs
- A crawl manifest (JSON) from the entrypoint, OR
- A report.json file (extract the crawl field)

Provide the manifest as a file path. Do not pass a live URL.

## Procedure
Execute these steps in order.

1. **Do not crawl the site yourself.** The entrypoint already crawled it.

2. **Load the evidence.** If you have a report.json, extract the crawl
   field and save it as a manifest file (e.g. manifest.json). If you only
   have a URL and no manifest, you cannot run this skill.

3. **Run the bundled script:**
   python {baseDir}/scripts/run.py <manifest.json>
   where {baseDir} is this skill's folder (skills/crawl-render-audit/).
   If you cannot run Python, skip rather than invent findings.

4. **Read the output.** The script prints JSON with ok: true and findings,
   or ok: false with a reason. Parse it.

5. **Return the findings.** Return the findings array from the script output.
   Do not rewrite or invent findings.

## Output
A list of findings consumed by the entrypoint composer.
See references/checks.md for the full check matrix (CR-001 through CR-012).

## Allowed tools
- GET HTTP requests (only to validate sameAs URLs or public corroboration)
- Parse HTML (from the manifest, not from live crawling)
- Read local files (the manifest, the SKILL.md, references/)
- Run the bundled Python script

NO writes to the target site. NO crawling the target site yourself.