import sys
import os
import json
import time
import urllib.request
import urllib.error
import threading

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.app import run_server

def start_server_in_thread(port):
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    time.sleep(1.0)
    return t

def test_endpoints():
    port = 8899
    start_server_in_thread(port)
    base_url = f"http://127.0.0.1:{port}"

    print(f"Testing API endpoints against {base_url}...")

    # 1. GET /
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "Incident Response Agent" in html
        assert "Analyze New Incident" in html
        assert "Synthetic Telemetry Feed" in html
        print("✓ GET / returns 200 with V2 dashboard HTML")

    # 2. GET /api/incidents
    req = urllib.request.Request(f"{base_url}/api/incidents")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data) == 12
        print(f"✓ GET /api/incidents returns {len(data)} synthetic incidents")

    # 3. GET /api/demo_sequence
    req = urllib.request.Request(f"{base_url}/api/demo_sequence")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data) == 5
        print(f"✓ GET /api/demo_sequence returns 5 events")

    # 4. GET /api/stats
    req = urllib.request.Request(f"{base_url}/api/stats")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        stats = json.loads(resp.read().decode("utf-8"))
        assert "instantly_resolved_count" in stats
        assert "bank_id" in stats
        print(f"✓ GET /api/stats returns status correctly (bank: {stats['bank_id']})")

    # 5. POST /api/handle_incident - Validation error (missing fields)
    bad_req = urllib.request.Request(
        f"{base_url}/api/handle_incident",
        data=json.dumps({"service": ""}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(bad_req)
        assert False, "Expected 400 Bad Request"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err_msg = json.loads(e.read().decode("utf-8"))
        assert "Validation failed" in err_msg.get("error", "")
        print("✓ POST /api/handle_incident rejects incomplete payloads with 400")

    # 6. POST /api/reset
    reset_req = urllib.request.Request(
        f"{base_url}/api/reset",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(reset_req) as resp:
        assert resp.status == 200
        print("✓ POST /api/reset resets counters successfully")

    print("\n✅ All HTTP API endpoint checks PASSED!")

if __name__ == "__main__":
    test_endpoints()
