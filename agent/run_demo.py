import sys
import os
import time
import json

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


def run_demo_narrative(bank_id: str = "demo-narrative-live"):
    print("=" * 80)
    print("🚀 INCIDENT RESPONSE AGENT - LIVE DEMO NARRATIVE")
    print(f"Memory Layer: Hindsight Cloud | Target Bank: '{bank_id}'")
    print("=" * 80)

    # Initialize isolated Hindsight client for this live demo
    hindsight = HindsightMemoryClient(bank_id=bank_id)
    llm = GroqLLMClient()
    agent = IncidentResponseAgent(hindsight_client=hindsight, llm_client=llm)
    dataset = IncidentDataset()

    # Section 6 demo steps:
    # Step 1: Incident #1 (payments-api DB pool exhaustion) - Novel
    # Step 2: Incident #2 (auth-service memory leak) - Unrelated novel
    # Step 3: Incident #3 (orders-api DB pool exhaustion) - Cross-service variant of #1 (Pattern Adaptation)
    # Step 4: Incident #4 (payments-api DB pool recurrence) - Exact recurrence of #1 (Fast path)
    # Step 5: Incident #5 (auth-service memory leak recurrence) - Exact recurrence of #2 (Fast path)

    demo_incidents = [
        dataset.get_by_id("INC-0001"),  # DB Pool Exhaustion in payments-api
        dataset.get_by_id("INC-0002"),  # Memory Leak in auth-service
        dataset.get_by_id("INC-0006"),  # DB Pool Exhaustion in orders-api (Variant)
        dataset.get_by_id("INC-0011"),  # DB Pool Recurrence in payments-api (Fast)
        dataset.get_by_id("INC-0012"),  # Memory Leak Recurrence in auth-service (Fast)
    ]

    for idx, inc in enumerate(demo_incidents, 1):
        print(f"\n{'='*30} DEMO EVENT {idx}/5 {'='*30}")
        print(f"Incoming Alert: [{inc['incident_id']}] {inc['service']}")
        print(f"Failure Family: {inc['failure_family']}")
        print(f"Error Signature: {inc['error_signature']}")
        print(f"Symptom: {inc['symptom']}")
        print("-" * 75)
        print("Agent is querying Hindsight memory and analyzing...")

        result = agent.handle_incident(inc)

        print(f"\n>>> AGENT ACTION: {result['tag']}")
        print(f"    Path: {result['path_taken']}")
        print(f"    Elapsed: {result['elapsed_seconds']}s")
        print(f"    Match Classification: {result['match_classification']}")
        if result.get("referenced_memory"):
            print(f"    Referenced Memory: {result['referenced_memory']}")

        diag = result["diagnosis"]
        headline = diag.get("headline", "")
        summary = diag.get("raw_llm_narrative", "")
        print(f"\n    [Headline]: {headline}")
        print(f"    [Remediation]: {diag.get('proven_fix') or diag.get('adapted_fix') or diag.get('recommended_fix')}")

        print(f"\n📊 LIVE METRIC COUNTERS:")
        print(f"    🧠 Resolved Instantly via Memory: {agent.instantly_resolved_count}")
        print(f"    🧬 Patterns Adapted Across Services: {agent.pattern_adapted_count}")
        print(f"    🔍 Novel Incidents Diagnosed & Learned: {agent.slow_diagnosed_count}")

        time.sleep(1.0)

    print("\n" + "=" * 80)
    print("✅ DEMO SEQUENCE COMPLETED SUCCESSFULLY!")
    print(f"Final Count of Incidents Accelerated by Hindsight Memory: {agent.instantly_resolved_count}/5")
    print(f"Final Count of Cross-Service Pattern Adaptations: {agent.pattern_adapted_count}")
    print("=" * 80)


if __name__ == "__main__":
    bank_name = sys.argv[1] if len(sys.argv) > 1 else "demo-narrative-live"
    run_demo_narrative(bank_name)
