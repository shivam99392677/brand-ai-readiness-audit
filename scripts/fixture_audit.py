"""Round 3 content QA: run the auditor against 4 tiny HTML fixtures (A-D) served
from a local HTTP server (no external network). Prints the findings per fixture so
a human can judge whether the sentences are true and evidenced.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator import AuditOrchestrator
from src.crawler.engine import CrawlConfig

WORDS = " ".join(
    f"word{i} firstline content paragraph filler text for orientation" for i in range(12)
)

FIXTURES = {
    # ---------------------------------------------------------------
    # Fixture A — REACH: GPTBot blocked in robots.txt, homepage fine
    # ---------------------------------------------------------------
    "A": {
        "port": 8801,
        "pages": {
            "/robots.txt": "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n",
            "/": f"""<!DOCTYPE html><html><head><title>Friendly SaaS - Homepage</title></head>
<body><h1>Friendly SaaS helps teams ship faster</h1>
<p>{WORDS}</p>
<nav><a href="/pricing">Pricing</a><a href="/about">About</a></nav>
</body></html>""",
            "/pricing": "<html><head><title>Pricing</title></head><body><h1>Pricing</h1><p>Plan A $10/mo</p></body></html>",
        },
    },
    # ---------------------------------------------------------------
    # Fixture B — EXTRACT: product page, visible price, broken JSON-LD
    # ---------------------------------------------------------------
    "B": {
        "port": 8802,
        "pages": {
            "/robots.txt": "User-agent: *\nAllow: /\n",
            "/": """<!DOCTYPE html><html><head><title>Widget Store</title></head>
<body><h1>Widget Store</h1><p>We sell widgets.</p><a href="/product/pro">Pro plan</a></body></html>""",
            "/product/pro": """<!DOCTYPE html><html><head><title>Pro Plan - Widget Store</title></head>
<body><h1>Pro Plan</h1>
<p>The Pro plan costs $49 / month and includes unlimited seats.</p>
<p>Cancel anytime. No setup fees.</p>
<script type="application/ld+json">{ "name": "Pro" </script>
</body></html>""",
        },
    },
    # ---------------------------------------------------------------
    # Fixture C — TRUST: price contradiction between /pricing and /docs
    # ---------------------------------------------------------------
    "C": {
        "port": 8803,
        "pages": {
            "/robots.txt": "User-agent: *\nAllow: /\n",
            "/": """<!DOCTYPE html><html><head><title>PlanCo</title></head>
<body><h1>PlanCo</h1><p>Simple plans for everyone.</p>
<nav><a href="/pricing">Pricing</a><a href="/docs">Docs</a></nav></body></html>""",
            "/pricing": "<html><head><title>Pricing</title></head><body><h1>Pricing</h1><p>Plan A $10/mo</p></body></html>",
            "/docs": "<html><head><title>Docs</title></head><body><h1>Docs</h1><p>Plan A $25/mo</p></body></html>",
        },
    },
    # ---------------------------------------------------------------
    # Fixture D — ENGAGEMENT: welcome H1, learn-more loop, deep page no breadcrumbs
    # ---------------------------------------------------------------
    "D": {
        "port": 8804,
        "pages": {
            "/robots.txt": "User-agent: *\nAllow: /\n",
            "/": f"""<!DOCTYPE html><html><head><title>Acme</title></head>
<body><h1>Welcome</h1>
<a href="#">Learn more</a>
<p>{WORDS}</p>
<nav><a href="/about/team">Team</a></nav>
</body></html>""",
            "/about/team": "<html><head><title>Our Team</title></head><body><h1>Our Team</h1><p>We are a small team of builders and operators.</p></body></html>",
        },
    },
}


class FixtureHandler(BaseHTTPRequestHandler):
    pages = {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "":
            path = "/"
        elif not path.startswith("/"):
            path = "/" + path
        body = self.pages.get(path)
        if body is None and path.endswith("/"):
            body = self.pages.get(path[:-1])
        if body is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def run_fixture(key, spec):
    handler = type(f"H{key}", (FixtureHandler,), {"pages": spec["pages"]})
    server = ThreadingHTTPServer(("127.0.0.1", spec["port"]), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{spec['port']}/"
    orch = AuditOrchestrator(
        crawl_config=CrawlConfig(max_pages=15, max_depth=2, discover_sitemap=False),
        enable_extended_skills=True,
    )
    report = orch.execute_audit(url, output_file=os.path.join("reports", f"fixture-{key}.json"))
    server.shutdown()
    return report


def summarize(key, report):
    path = os.path.join("reports", f"fixture-{key}.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    print(f"\n{'=' * 70}\nFIXTURE {key} — composed report: {data.get('summary')}")
    for f in data.get("findings", []):
        print(f"\n[{f.get('check_id')}] sev={f.get('severity')} | {f.get('title')}")
        print(f"  evidence: {f.get('evidence', '')[:400]}")
        print(f"  urls: {f.get('affected_urls')}")
        print(f"  action: {f.get('suggested_action', {}).get('summary', '')[:200]}")


if __name__ == "__main__":
    only = sys.argv[1:] or ["A", "B", "C", "D"]
    for k in only:
        rep = run_fixture(k, FIXTURES[k])
        summarize(k, rep)
