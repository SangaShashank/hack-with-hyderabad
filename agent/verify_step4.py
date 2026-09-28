import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json
from agent.main import IncidentResponseAgent
from agent.hindsight_client import HindsightMemoryClient

UNSEEN_INCIDENT = {
    "incident_id": "INC-0002",
    "service": "auth-service",
    "symptom": "Pod crash loops with OOMKilled exit code 137, RSS memory growing monotonically",
    "error_signature": "NodeOOMAlert: container auth-service killed by cgroup memory limit 512Mi",
    "timestamp": "2026-09-27T19:00:00Z"
}

def main():
    print("=" * 75)
    print("STEP 4: No Match Found Path (Reason from scratch & Retain into Hindsight)")
    print("=" * 75)
    print("New Incoming Incident with NO prior memory:")
    print(json.dumps(UNSEEN_INCIDENT, indent=2))
    print("-" * 75)

    agent = IncidentResponseAgent()

    print("\n[Phase 1] Processing Unseen Incident via agent.handle_incident()...")
    result = agent.handle_incident(UNSEEN_INCIDENT)

    print("\n" + "=" * 75)
    print("--- LIVE AGENT SLOW-PATH OUTPUT ---")
    print("=" * 75)
    print(f"Path Taken: {result.get('path_taken')} ({result.get('tag')})")
    print(f"Elapsed Time: {result.get('elapsed_seconds')}s")
    print(f"Retained to Hindsight Memory: {result.get('retained_to_memory')}")
    print(f"Retain API Response: {result.get('retain_response')}")
    print("\nLLM Diagnosis Generated from First Principles:")
    print(json.dumps(result.get("diagnosis"), indent=2))

    print("-" * 75)
    print("\n[Phase 2] Verifying that Hindsight Memory now possesses this new knowledge...")
    with HindsightMemoryClient() as hindsight:
        query = f"{UNSEEN_INCIDENT['service']} {UNSEEN_INCIDENT['error_signature']}"
        recalled = hindsight.recall(query=query)
        matches = hindsight.recall_incident_matches(query=query)

        print(f"Recall Query: '{query}'")
        print(f"Total Matches in Hindsight: {len(recalled.results)}")
        for i, m in enumerate(matches, 1):
            scores = m.get("scores", {})
            print(f"\nRecalled Memory Item #{i}:")
            print(f"  • Type: {m['type']}")
            print(f"  • Tags: {m['tags']}")
            print(f"  • Scores: {scores}")
            print(f"  • Text: {m['text'][:120]}...")

    print("=" * 75)
    assert result.get("path_taken") == "slow_path", "Expected slow_path for unseen incident"
    assert result.get("retained_to_memory") is True, "Expected retain_to_memory to be True"
    assert len(recalled.results) > 0, "Expected Hindsight to have retained the new incident"
    print("CONFIRMATION: Step 4 complete! Novel incident reasoned from scratch and retained to Hindsight.")

if __name__ == "__main__":
    main()
