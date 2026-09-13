# `gui/` — Interactive Test Harness

**Business logic:** a judge-friendly visual inspector. Running `python -m gui.app` serves a single page where anyone can launch an audit and see findings rendered as severity badges, titles, evidence, and suggested actions — no JSON squinting. It exists to *show* the report, never to change it.

**Tech logic:** `app.py` binds a lightweight `HTTPServer` to `0.0.0.0:8080`, handles GET (serve HTML_TEMPLATE) and POST (run `AuditOrchestrator(enable_extended_skills=True)` with the submitted URL and bounds, then compose `AdobeReportComposer` output into HTML rows). Findings render with severity badge classes, `check_id` + category under the title, evidence text, and `[PRIORITY]`-tagged actions.

```mermaid
flowchart TD
    B["python -m gui.app"] --> S["HTTPServer 0.0.0.0:8080"]
    S --> GET{"request type"}
    GET -->|GET /| T["HTML_TEMPLATE form: url + max-pages + max-depth"]
    T --> U["user submits target"]
    U --> POST["POST / -> AuditOrchestrator(enable_extended_skills=True)"]
    POST --> AUD["execute_audit(url, bounds)"]
    AUD --> F["findings[]"]
    F --> R["render rows: severity badge, title plus category and check_id, evidence, priority-tagged action"]
    R --> BROWSER["localhost:8080 in browser"]
```

### `app.py`
**Business:** the demo surface — a person with no terminal can audit example.com and read the findings.
**Tech:** single-file server; orchestrator + composer reused directly (the GUI adds zero audit logic, so the harness always shows exactly what the CLI would produce).

```mermaid
flowchart LR
    A["AuditHandler"] --> B["do_GET -> template"]
    A --> C["do_POST -> orchestrator + composer"]
    C --> D["findings -> HTML table rows"]
    D --> E["identical content to CLI report.json"]
```

**Parent:** [repository root README](../README.md).