import sys
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.hindsight_client import HindsightMemoryClient
from agent.llm_client import GroqLLMClient
from agent.main import IncidentResponseAgent
from agent.incidents import IncidentDataset

DATASET = IncidentDataset()
HINDSIGHT = HindsightMemoryClient()
LLM = GroqLLMClient()
AGENT = IncidentResponseAgent(hindsight_client=HINDSIGHT, llm_client=LLM)


class DemoServerHandler(BaseHTTPRequestHandler):

    def _set_headers(self, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(status=200)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            html_path = os.path.join(script_dir, "index.html")
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._set_headers(content_type="text/html", status=200)
                self.wfile.write(content.encode("utf-8"))
            else:
                self._set_headers(status=404)
                self.wfile.write(b"index.html not found")

        elif path == "/api/incidents":
            incidents = DATASET.get_all()
            self._set_headers(status=200)
            self.wfile.write(json.dumps(incidents).encode("utf-8"))

        elif path == "/api/demo_sequence":
            sequence = DATASET.get_demo_sequence()
            self._set_headers(status=200)
            self.wfile.write(json.dumps(sequence).encode("utf-8"))

        elif path == "/api/stats":
            stats = {
                "instantly_resolved_count": AGENT.instantly_resolved_count,
                "pattern_adapted_count": AGENT.pattern_adapted_count,
                "slow_diagnosed_count": AGENT.slow_diagnosed_count,
                "bank_id": HINDSIGHT.bank_id,
            }
            self._set_headers(status=200)
            self.wfile.write(json.dumps(stats).encode("utf-8"))

        else:
            self._set_headers(status=404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        if path == "/api/handle_incident":
            try:
                incident_data = json.loads(body)
                result = AGENT.handle_incident(incident_data)
                self._set_headers(status=200)
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self._set_headers(status=500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif path == "/api/reset":
            AGENT.instantly_resolved_count = 0
            AGENT.pattern_adapted_count = 0
            AGENT.slow_diagnosed_count = 0
            self._set_headers(status=200)
            self.wfile.write(json.dumps({"status": "counters_reset"}).encode("utf-8"))

        else:
            self._set_headers(status=404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


def run_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DemoServerHandler)
    print(f"Server started on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
