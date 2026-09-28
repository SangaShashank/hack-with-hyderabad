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

CROSS_SERVICE_INCIDENT = {
    "incident_id": "INC-0003",
    "service": "orders-api",
    "symptom": "Checkout requests failing during flash sale, DB connection timeouts spiking",
    "error_signature": "ConnectionPoolTimeoutError: pool exhausted after 30000ms",
    "timestamp": "2026-09-27T19:30:00Z"
}

def main():
    print("=" * 75)
    print("STEP 5: Partial-Match / Pattern-Adaptation Verification")
    print("=" * 75)
    print("Incoming Variant Incident in DIFFERENT Service (orders-api vs payments-api):")
    print(json.dumps(CROSS_SERVICE_INCIDENT, indent=2))
    print("-" * 75)

    agent = IncidentResponseAgent()

    print("\n[Phase 1] Processing Incident through IncidentResponseAgent...")
    result = agent.handle_incident(CROSS_SERVICE_INCIDENT)

    print("\n" + "=" * 75)
    print("--- LIVE AGENT PATTERN-ADAPTATION OUTPUT ---")
    print("=" * 75)
    print(f"Path Taken: {result.get('path_taken')}")
    print(f"Tag: {result.get('tag')}")
    print(f"Match Classification: {result.get('match_classification')}")
    print(f"Referenced Prior Memory Tags: {result.get('referenced_memory')}")
    print(f"Top Similarity Scores: {result.get('top_score')}")
    print(f"Elapsed Time: {result.get('elapsed_seconds')}s")
    print(f"Retained Adapted Knowledge to Hindsight: {result.get('retained_to_memory')}")
    print(f"Instantly/Rapidly Resolved Counter: {result.get('instantly_resolved_counter')}")
    print(f"Pattern Adapted Counter: {result.get('pattern_adapted_counter')}")

    diagnosis = result.get("diagnosis", {})
    print("\n--- ADAPTED DIAGNOSIS & REMEDIATION (NOT RAW REPLAY) ---")
    print(json.dumps(diagnosis, indent=2))

    print("-" * 75)
    print("\n--- VERIFICATION CHECKS ---")
    assert result.get("path_taken") == "pattern_adapted_path", f"Expected pattern_adapted_path, got {result.get('path_taken')}"
    assert result.get("match_classification") == "partial_match", f"Expected partial_match, got {result.get('match_classification')}"
    assert diagnosis.get("source") == "pattern_adaptation", "Expected source to be pattern_adaptation"

    print("✓ Path Correctly Classified: pattern_adapted_path (🧬 Pattern adapted from memory)")
    print(f"✓ Pattern Family Identified: {diagnosis.get('pattern_family')}")
    print(f"✓ Prior Incident Referenced: {diagnosis.get('referenced_incident')}")
    print(f"✓ Adaptation Notes: {diagnosis.get('adaptation_notes')[:100]}...")
    print(f"✓ Adapted Fix for orders-api: {diagnosis.get('adapted_fix')[:100]}...")

    print("=" * 75)
    print("CONFIRMATION: Step 5 complete! The agent successfully recognized the past pattern and adapted the fix to the new service.")

if __name__ == "__main__":
    main()
