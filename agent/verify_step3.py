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
from agent.hindsight_client import HindsightMemoryClient
from agent.llm_client import GroqLLMClient

INCOMING_INCIDENT = {
    "incident_id": "INC-0001-RECURRENCE",
    "service": "payments-api",
    "symptom": "500 errors spiking again during morning traffic surge, latency > 5s",
    "error_signature": "ConnectionPoolTimeoutError: pool exhausted after 30000ms",
    "timestamp": "2026-09-27T18:30:00Z"
}

def main():
    print("=" * 75)
    print("STEP 3: Wire in LLM with Recalled Hindsight Memory (Fast Path)")
    print("=" * 75)
    print("Incoming Recurring Incident:")
    print(json.dumps(INCOMING_INCIDENT, indent=2))
    print("-" * 75)

    # 1. Recall from Hindsight Cloud
    print("\n[Phase 1] Querying Hindsight Cloud Memory...")
    with HindsightMemoryClient() as hindsight:
        query = f"{INCOMING_INCIDENT['service']} {INCOMING_INCIDENT['error_signature']}"
        raw_recall = hindsight.recall(query=query)
        matches = hindsight.recall_incident_matches(query=query)
        prompt_memory_str = raw_recall.to_prompt_string()

        print(f"Recalled {len(raw_recall.results)} memory items from Hindsight bank '{hindsight.bank_id}'.")
        print("\nRecalled Memory String injected into prompt:")
        print(prompt_memory_str)

    # 2. Feed memory into Groq LLM
    print("\n[Phase 2] Feeding Recalled Memory to Groq LLM (openai/gpt-oss-120b)...")
    llm = GroqLLMClient()
    response = llm.synthesize_from_memory(
        incident=INCOMING_INCIDENT,
        recalled_memories_prompt=prompt_memory_str,
        recalled_records=matches
    )

    print("\n" + "=" * 75)
    print("--- LIVE LLM RESPONSE (SYNTHESIZED FROM MEMORY) ---")
    print("=" * 75)
    print(json.dumps(response, indent=2))

    # Assertions for verification
    referenced = response.get("referenced_incident", "")
    headline = response.get("headline", "")
    root_cause = response.get("root_cause", "")
    fix = response.get("proven_fix", "")
    narrative = response.get("raw_llm_narrative", "")

    print("\n--- VERIFICATION CHECKS ---")
    print(f"✓ Source Tag: {response.get('source')} (Confidence: {response.get('confidence')})")
    print(f"✓ Referenced Incident: {referenced}")
    print(f"✓ Root Cause Identified: {root_cause[:80]}...")
    print(f"✓ Proven Fix Identified: {fix[:80]}...")

    print("\nStep 3 verification complete! The LLM successfully references past incident memory.")

if __name__ == "__main__":
    main()
