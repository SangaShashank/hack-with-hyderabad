

import sys, os
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from agent.hindsight_client import HindsightMemoryClient

SAMPLE_INCIDENT = {
    "incident_id": "INC-0001",
    "service": "payments-api",
    "symptom": "500 errors spiking, latency > 5s",
    "error_signature": "ConnectionPoolTimeoutError: pool exhausted after 30000ms",
    "root_cause": "DB connection pool size too low for traffic spike during batch job",
    "fix_applied": "Increased pool size from 10 to 50, added circuit breaker",
    "timestamp": "2026-09-20T03:14:00Z"
}

def main():
    print("=" * 60)
    print("STEP 1: Retain ONE incident in Hindsight Cloud Memory")
    print("=" * 60)
    print("Incident payload to retain:")
    print(json.dumps(SAMPLE_INCIDENT, indent=2))
    print("-" * 60)
    
    client = HindsightMemoryClient()
    print(f"Connecting to Hindsight Cloud API at: {client.base_url}")
    print(f"Target Bank ID: {client.bank_id}")
    print("Calling client.retain_incident()...")
    
    response = client.retain_incident(SAMPLE_INCIDENT)
    
    print("\n--- LIVE API RESPONSE ---")
    print(f"Type: {type(response)}")
    print(f"Success: {getattr(response, 'success', None)}")
    print(f"Bank ID: {getattr(response, 'bank_id', None)}")
    print(f"Items Count: {getattr(response, 'items_count', None)}")
    print(f"Async: {getattr(response, 'var_async', None)}")
    print(f"Usage: {getattr(response, 'usage', None)}")
    print(f"Full Response Object: {repr(response)}")
    print("-" * 60)
    print("Step 1 retain execution complete!")

if __name__ == "__main__":
    main()
