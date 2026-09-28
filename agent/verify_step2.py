import sys, os
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from agent.hindsight_client import HindsightMemoryClient

QUERY_INCIDENT = {
    "service": "payments-api",
    "error_signature": "ConnectionPoolTimeoutError: pool exhausted after 30000ms",
    "symptom": "500 errors spiking, latency > 5s"
}

def main():
    print("=" * 70)
    print("STEP 2: Recall Memory from Hindsight Cloud for INC-0001")
    print("=" * 70)
    
    query = f"{QUERY_INCIDENT['service']} {QUERY_INCIDENT['error_signature']}"
    print(f"Recall Query: '{query}'")
    print("-" * 70)

    with HindsightMemoryClient() as client:
        print(f"Querying Bank ID: '{client.bank_id}' on {client.base_url}...")
        raw_response = client.recall(query=query)
        matches = client.recall_incident_matches(query=query)

        print("\n--- RAW RECALL RESPONSE SUMMARY ---")
        print(f"Total results returned: {len(raw_response.results)}")

        print("\n--- RECALLED RECORDS (FACTS & OBSERVATIONS) ---")
        for i, m in enumerate(matches, 1):
            scores = m.get("scores", {})
            semantic = scores.get("semantic", "N/A")
            reranker = scores.get("reranker", "N/A")
            final_score = scores.get("final", "N/A")
            print(f"\nResult #{i}:")
            print(f"  • Type: {m['type']}")
            print(f"  • Tags: {m['tags']}")
            print(f"  • Scores: [Final: {final_score}, Semantic: {semantic}, Reranker: {reranker}]")
            print(f"  • Content: {m['text']}")

        print("\n--- HINDSIGHT STRUCTURED CONTEXT (to_prompt_string) ---")
        print(raw_response.to_prompt_string())

        print("=" * 70)
        assert len(raw_response.results) > 0, "Expected at least 1 memory match from Hindsight!"
        print("CONFIRMATION: Incident INC-0001 record successfully recalled from Hindsight Cloud!")

if __name__ == "__main__":
    main()
