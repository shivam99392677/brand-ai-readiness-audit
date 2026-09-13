"""Minimal GUI Test Harness for Brand AI Readiness Audit.

Runs a lightweight local web server on port 8080 allowing users to input a target URL,
execute the full 6-skill audit pipeline via AuditOrchestrator, and inspect the
resulting Adobe JSON report and findings table.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

# Ensure repository root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.orchestrator import AuditOrchestrator
from src.reporting.composer import compose_adobe_report

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brand AI Readiness Audit — Test Harness</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --critical: #ef4444;
            --high: #f97316;
            --medium: #eab308;
            --low: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 2rem; max-width: 1200px; margin: 0 auto; line-height: 1.5; }
        header { margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }
        h1 { font-size: 1.75rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; }
        p.subtitle { color: var(--text-muted); font-size: 0.95rem; }
        .audit-form { display: flex; gap: 1rem; margin-bottom: 2rem; }
        input[type="url"] {
            flex: 1; padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border);
            background: var(--card-bg); color: var(--text); font-size: 1rem; outline: none;
        }
        input[type="url"]:focus { border-color: var(--primary); }
        button {
            padding: 0.75rem 1.5rem; border-radius: 8px; border: none; background: var(--primary);
            color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s;
        }
        button:hover { background: var(--primary-hover); }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .summary-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; text-align: center; }
        .summary-card .count { font-size: 2rem; font-weight: 700; margin-top: 0.25rem; }
        .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .badge-critical { background: rgba(239, 68, 68, 0.2); color: var(--critical); border: 1px solid var(--critical); }
        .badge-high { background: rgba(249, 115, 22, 0.2); color: var(--high); border: 1px solid var(--high); }
        .badge-medium { background: rgba(234, 179, 8, 0.2); color: var(--medium); border: 1px solid var(--medium); }
        .badge-low { background: rgba(16, 185, 129, 0.2); color: var(--low); border: 1px solid var(--low); }
        table { width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); margin-bottom: 2rem; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
        th { background: #111827; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.8rem; }
        tr:last-child td { border-bottom: none; }
        .code-box { background: #0b0f19; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; overflow-x: auto; font-family: monospace; font-size: 0.85rem; color: #a5f3fc; }
        .loading { display: none; text-align: center; padding: 2rem; color: var(--text-muted); }
    </style>
</head>
<body>
    <header>
        <h1>Brand AI Readiness Audit</h1>
        <p class="subtitle">Agent Skill Marketplace Test Harness & Adobe Report Inspector</p>
    </header>

    <form class="audit-form" method="GET" action="/" onsubmit="document.getElementById('loading').style.display='block';">
        <input type="url" name="url" placeholder="https://example.com" value="__TARGET_URL__" required>
        <button type="submit">Run Audit</button>
    </form>

    <div id="loading" class="loading">Auditing domain with 6 analysis skills... Please wait.</div>

    __AUDIT_RESULTS__

</body>
</html>
"""


class AuditHandler(BaseHTTPRequestHandler):
    """HTTP request handler for local GUI test harness."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        target_url = params.get("url", [""])[0].strip()

        if target_url:
            try:
                # Match the judges' default CLI: extended skills (sitemap + AI bot
                # blocks) are part of the default audit path.
                orchestrator = AuditOrchestrator(enable_extended_skills=True)
                report = orchestrator.execute_audit(target_url)
                adobe_report = compose_adobe_report(target_url, report.findings)
                rendered_html = self._render_report(target_url, adobe_report)
            except Exception as e:
                rendered_html = f"<div style='color: #ef4444; background: #1e293b; padding: 1.5rem; border-radius: 8px;'><h3>Audit Error</h3><p>{str(e)}</p></div>"
        else:
            rendered_html = "<p style='color: var(--text-muted); text-align: center; padding: 3rem;'>Enter a website URL above and click <strong>Run Audit</strong> to evaluate its AI readiness.</p>"

        response_body = HTML_TEMPLATE.replace("__TARGET_URL__", target_url).replace("__AUDIT_RESULTS__", rendered_html)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(response_body.encode("utf-8"))

    def _render_report(self, target_url: str, adobe_report: dict) -> str:
        summary = adobe_report.get("summary", {})
        findings = adobe_report.get("findings", [])

        summary_html = f"""
        <div class="summary-grid">
            <div class="summary-card">
                <div style="color: var(--text-muted); font-size: 0.85rem;">Total Findings</div>
                <div class="count">{summary.get('total_findings', 0)}</div>
            </div>
            <div class="summary-card">
                <div style="color: var(--critical); font-size: 0.85rem;">Critical</div>
                <div class="count" style="color: var(--critical);">{summary.get('critical', 0)}</div>
            </div>
            <div class="summary-card">
                <div style="color: var(--high); font-size: 0.85rem;">High</div>
                <div class="count" style="color: var(--high);">{summary.get('high', 0)}</div>
            </div>
            <div class="summary-card">
                <div style="color: var(--medium); font-size: 0.85rem;">Medium</div>
                <div class="count" style="color: var(--medium);">{summary.get('medium', 0)}</div>
            </div>
            <div class="summary-card">
                <div style="color: var(--low); font-size: 0.85rem;">Low</div>
                <div class="count" style="color: var(--low);">{summary.get('low', 0)}</div>
            </div>
        </div>
        """

        rows_html = ""
        for f in findings:
            sev = f.get("severity", "low")
            badge_class = f"badge badge-{sev}"
            sugg = f.get("suggested_action", {})
            action_text = sugg.get("summary", "") if isinstance(sugg, dict) else str(sugg)
            priority_val = sugg.get("priority", sev) if isinstance(sugg, dict) else sev

            rows_html += f"""
            <tr>
                <td style="font-weight: 700; color: #fff;">{f.get('id', '')}</td>
                <td><span class="{badge_class}">{sev}</span></td>
                <td><strong>{f.get('title', '')}</strong><br><small style="color: var(--text-muted);">{f.get('category', '')} ({f.get('check_id', '')})</small></td>
                <td style="color: #cbd5e1; max-width: 350px;">{f.get('evidence', '')}</td>
                <td><span style="font-size: 0.85rem; color: #93c5fd;">[{priority_val.upper()}]</span> {action_text}</td>
            </tr>
            """

        if not rows_html:
            rows_html = "<tr><td colspan='5' style='text-align: center; color: var(--low); padding: 2rem;'>🎉 No actionable defects found! All executed checks passed.</td></tr>"

        table_html = f"""
        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem;">Audit Findings</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 80px;">ID</th>
                    <th style="width: 100px;">Severity</th>
                    <th style="width: 280px;">Title & Category</th>
                    <th>Evidence Summary</th>
                    <th style="width: 300px;">Suggested Action</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem;">Adobe Report JSON (Canonical)</h2>
        <pre class="code-box">{json.dumps(adobe_report, indent=2)}</pre>
        """

        return summary_html + table_html


def run_server(host: str = "0.0.0.0", port: int = 8080):
    server_address = (host, port)
    httpd = HTTPServer(server_address, AuditHandler)
    print(f"Brand AI Readiness Audit GUI running at http://localhost:{port}/ (bound to {host}:{port})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GUI server...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port=port_arg)
