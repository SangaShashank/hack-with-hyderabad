import sys
import os
import json
import time
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if sys.path and os.path.abspath(sys.path[0]) == script_dir:
    sys.path.pop(0)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent.main import IncidentResponseAgent
from agent.hindsight_client import HindsightMemoryClient
from agent.llm_client import GroqLLMClient

def run_tests():
    print("=" * 80)
    print("🧪 VERSION 2 VERIFICATION SUITE: OPERATOR LEARNING LOOP (A, B, C)")
    print("=" * 80)

    unique_run_id = str(int(time.time()))[-5:]
    test_bank = f"test-loop-{unique_run_id}"
    hindsight = HindsightMemoryClient(bank_id=test_bank)
    agent = IncidentResponseAgent(hindsight_client=hindsight)

    # Reset counters for clean test tracking
    agent.instantly_resolved_count = 0
    agent.pattern_adapted_count = 0
    agent.slow_diagnosed_count = 0

    novel_service = f"mesh-router-{unique_run_id}"
    novel_error = f"ConsulCatalogDiscoveryTimeout-{unique_run_id}: catalog query timed out on mesh agent node"
    novel_symptom = "Outbound service mesh calls failing with 503 Service Unavailable, consul agent RPC unreachable"

    # ---------------------------------------------------------
    # TEST A: Novel User Incident
    # ---------------------------------------------------------
    print("\n[TEST A] Submitting novel user incident (Unseen failure & service)...")
    novel_incident = {
        "service": novel_service,
        "error_signature": novel_error,
        "symptoms": novel_symptom,
    }
    print("Payload:")
    print(json.dumps(novel_incident, indent=2))

    res_a = agent.handle_incident(novel_incident)
    print(f"\nResult A:")
    print(f"  • Incident ID: {res_a.get('incident_id')}")
    print(f"  • Path Taken: {res_a.get('path_taken')}")
    print(f"  • Tag: {res_a.get('tag')}")
    print(f"  • Match Classification: {res_a.get('match_classification')}")
    print(f"  • Elapsed: {res_a.get('elapsed_seconds')}s")
    print(f"  • Retained to Memory: {res_a.get('retained_to_memory')}")
    print(f"  • Diagnosis Headline: {res_a.get('diagnosis', {}).get('headline')}")

    assert res_a.get("incident_id", "").startswith("USER-"), "Expected auto-generated USER- ID"
    assert res_a.get("path_taken") == "slow_path", f"Expected slow_path, got {res_a.get('path_taken')}"
    assert res_a.get("tag") == "🔍 New diagnosis", f"Expected '🔍 New diagnosis', got {res_a.get('tag')}"
    assert res_a.get("retained_to_memory") is True, "Expected retained_to_memory to be True"
    print("✅ TEST A PASSED: Novel user incident reasoned from scratch & retained into Hindsight memory.")

    # Allow Hindsight cloud bank indexing
    print("\nWaiting 3 seconds for Hindsight cloud indexing...")
    time.sleep(3.0)

    # ---------------------------------------------------------
    # TEST B: Repeat Incident (Same service & failure)
    # ---------------------------------------------------------
    print("\n[TEST B] Submitting recurring incident in the same service...")
    repeat_incident = {
        "service": novel_service,
        "error_signature": novel_error,
        "symptoms": f"Outbound mesh calls failing again after consul agent restart ({unique_run_id})",
    }
    print("Payload:")
    print(json.dumps(repeat_incident, indent=2))

    res_b = agent.handle_incident(repeat_incident)
    print(f"\nResult B:")
    print(f"  • Incident ID: {res_b.get('incident_id')}")
    print(f"  • Path Taken: {res_b.get('path_taken')}")
    print(f"  • Tag: {res_b.get('tag')}")
    print(f"  • Match Classification: {res_b.get('match_classification')}")
    print(f"  • Elapsed: {res_b.get('elapsed_seconds')}s")
    print(f"  • Referenced Memory: {res_b.get('referenced_memory')}")
    print(f"  • Diagnosis Headline: {res_b.get('diagnosis', {}).get('headline')}")
    print(f"  • Proven Fix: {res_b.get('diagnosis', {}).get('proven_fix')}")

    assert res_b.get("path_taken") == "fast_path", f"Expected fast_path, got {res_b.get('path_taken')}"
    assert res_b.get("tag") == "🧠 Recalled from memory", f"Expected '🧠 Recalled from memory', got {res_b.get('tag')}"
    assert res_b.get("match_classification") == "strong_match", f"Expected strong_match, got {res_b.get('match_classification')}"
    print("✅ TEST B PASSED: Repeated incident successfully recalled from Hindsight memory (Fast Path).")

    # ---------------------------------------------------------
    # TEST C: Cross-Service Variant
    # ---------------------------------------------------------
    print("\n[TEST C] Submitting similar failure family in a DIFFERENT service...")
    diff_service = f"edge-gateway-{unique_run_id}"
    cross_incident = {
        "service": diff_service,
        "error_signature": novel_error,
        "symptoms": "Edge gateway cannot locate downstream mesh services via consul catalog",
    }
    print("Payload:")
    print(json.dumps(cross_incident, indent=2))

    res_c = agent.handle_incident(cross_incident)
    print(f"\nResult C:")
    print(f"  • Incident ID: {res_c.get('incident_id')}")
    print(f"  • Path Taken: {res_c.get('path_taken')}")
    print(f"  • Tag: {res_c.get('tag')}")
    print(f"  • Match Classification: {res_c.get('match_classification')}")
    print(f"  • Elapsed: {res_c.get('elapsed_seconds')}s")
    print(f"  • Referenced Memory: {res_c.get('referenced_memory')}")
    print(f"  • Pattern Family: {res_c.get('diagnosis', {}).get('pattern_family')}")
    print(f"  • Adaptation Notes: {res_c.get('diagnosis', {}).get('adaptation_notes')}")
    print(f"  • Adapted Fix: {res_c.get('diagnosis', {}).get('adapted_fix')}")

    assert res_c.get("path_taken") == "pattern_adapted_path", f"Expected pattern_adapted_path, got {res_c.get('path_taken')}"
    assert res_c.get("tag") == "🧬 Pattern adapted from memory", f"Expected '🧬 Pattern adapted from memory', got {res_c.get('tag')}"
    assert res_c.get("match_classification") == "partial_match", f"Expected partial_match, got {res_c.get('match_classification')}"
    assert res_c.get("diagnosis", {}).get("source") == "pattern_adaptation", "Expected diagnosis source to be pattern_adaptation"
    print("✅ TEST C PASSED: Cross-service pattern recognized & adapted specifically for new service.")

    # ---------------------------------------------------------
    # COUNTERS CHECK
    # ---------------------------------------------------------
    print("\n--- METRIC COUNTERS VERIFICATION ---")
    print(f"Resolved via Memory: {agent.instantly_resolved_count}")
    print(f"Patterns Adapted: {agent.pattern_adapted_count}")
    assert agent.slow_diagnosed_count == 1, f"Expected slow_diagnosed_count == 1, got {agent.slow_diagnosed_count}"
    assert agent.pattern_adapted_count == 1, f"Expected pattern_adapted_count == 1, got {agent.pattern_adapted_count}"
    assert agent.instantly_resolved_count == 1, f"Expected instantly_resolved_count == 1, got {agent.instantly_resolved_count}"
    total = agent.instantly_resolved_count + agent.pattern_adapted_count + agent.slow_diagnosed_count
    assert total == 3, f"Expected total processed == 3, got {total}"
    print(f"Total Processed Incidents: {total}/3 (Clean 1:1 mutually exclusive partition)")

    print("\n" + "=" * 80)
    print("🏆 ALL VERSION 2 LEARNING LOOP TESTS (A, B, C) PASSED PERFECTLY!")
    print("=" * 80)

    try:
        hindsight.client.delete_bank(test_bank)
    except Exception:
        pass

if __name__ == "__main__":
    run_tests()
