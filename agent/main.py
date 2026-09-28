import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

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


class IncidentResponseAgent:
    """
    Core Incident Response Agent leveraging Hindsight Memory and Groq LLM.
    Implements the dual-path architecture:
      - Fast Path: Instant resolution when pattern is recognized from Hindsight memory.
      - Slow Path: First-principles LLM diagnosis when novel, automatically retained to memory.
    """

    # Design Decision: Reranker/Final score threshold to consider a memory match strong
    # Scores >= 0.60 indicate high confidence match (Fast Path)
    # Scores between 0.30 and 0.60 indicate partial match / pattern adaptation
    # Scores < 0.30 indicate completely novel incident (Slow Path)
    STRONG_MATCH_THRESHOLD = 0.60
    PARTIAL_MATCH_THRESHOLD = 0.30

    def __init__(
        self,
        hindsight_client: Optional[HindsightMemoryClient] = None,
        llm_client: Optional[GroqLLMClient] = None,
    ):
        self.hindsight = hindsight_client or HindsightMemoryClient()
        self.llm = llm_client or GroqLLMClient()
        self.instantly_resolved_count = 0
        self.pattern_adapted_count = 0
        self.slow_diagnosed_count = 0

    def evaluate_memory_matches(
        self,
        matches: List[Dict[str, Any]],
        incoming_service: str,
    ) -> Tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Evaluate recall matches to classify into:
          - 'strong_match': Identical service and high similarity
          - 'partial_match': Cross-service or variant sharing the same failure pattern
          - 'no_match': Novel failure pattern with low similarity
        """
        if not matches:
            return "no_match", None, []

        top_match = matches[0]
        scores = top_match.get("scores", {})
        reranker_score = scores.get("reranker")
        final_score = scores.get("final")
        semantic_score = scores.get("semantic", 0.0) or 0.0
        tags = top_match.get("tags", []) or []
        match_text = top_match.get("text", "").lower()

        # Check if matched memory belongs to the same service
        is_same_service = incoming_service.lower() in [t.lower() for t in tags] or incoming_service.lower() in match_text

        effective_score = reranker_score if reranker_score is not None else final_score
        if effective_score is None:
            effective_score = semantic_score

        # Case 1: Exact / strong match on same service
        if is_same_service and effective_score >= self.STRONG_MATCH_THRESHOLD:
            return "strong_match", top_match, matches

        # Case 2: Cross-service pattern or structural variant
        # If semantic similarity is high (>= 0.70) or reranker indicates failure pattern match
        if (not is_same_service and (semantic_score >= 0.68 or effective_score >= self.PARTIAL_MATCH_THRESHOLD)) or \
           (is_same_service and self.PARTIAL_MATCH_THRESHOLD <= effective_score < self.STRONG_MATCH_THRESHOLD):
            return "partial_match", top_match, matches

        # Case 3: Very high overall similarity even across services (fallback strong match if score is extremely high)
        if effective_score >= 0.85:
            return "strong_match", top_match, matches

        return "no_match", None, []

    def handle_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming incident record through Hindsight memory and LLM.
        """
        start_time = time.time()
        service = incident.get("service", "unknown-service")
        error_sig = incident.get("error_signature", "")
        symptom = incident.get("symptom", "")

        query = f"{service} {error_sig} {symptom}".strip()

        # Step A: Check Hindsight Memory Bank
        raw_recall = self.hindsight.recall(query=query)
        matches = self.hindsight.recall_incident_matches(query=query)
        prompt_string = raw_recall.to_prompt_string()

        match_classification, top_match, relevant_matches = self.evaluate_memory_matches(matches, service)

        # 1. FAST PATH: Strong Match in Memory (Exact recurrence)
        if match_classification == "strong_match":
            self.instantly_resolved_count += 1
            diagnosis = self.llm.synthesize_from_memory(
                incident=incident,
                recalled_memories_prompt=prompt_string,
                recalled_records=relevant_matches,
            )
            elapsed = time.time() - start_time
            return {
                "incident_id": incident.get("incident_id"),
                "service": service,
                "path_taken": "fast_path",
                "tag": "🧠 Recalled from memory",
                "elapsed_seconds": round(elapsed, 3),
                "match_classification": match_classification,
                "top_score": top_match.get("scores") if top_match else None,
                "referenced_memory": top_match.get("tags") if top_match else [],
                "diagnosis": diagnosis,
                "instantly_resolved_counter": self.instantly_resolved_count,
            }

        # 2. PATTERN ADAPTATION PATH: Partial Match across services / variants
        elif match_classification == "partial_match":
            self.pattern_adapted_count += 1
            self.instantly_resolved_count += 1  # Counted as memory-assisted rapid resolution
            diagnosis = self.llm.adapt_pattern_from_memory(
                incident=incident,
                recalled_memories_prompt=prompt_string,
                recalled_records=relevant_matches,
            )

            # Auto-retain adapted fix to Hindsight memory for this new service
            retain_payload = {
                "incident_id": incident.get("incident_id"),
                "service": service,
                "symptom": symptom,
                "error_signature": error_sig,
                "root_cause": diagnosis.get("pattern_explanation", ""),
                "fix_applied": diagnosis.get("adapted_fix", ""),
                "timestamp": incident.get("timestamp", ""),
            }
            retain_res = self.hindsight.retain_incident(
                incident=retain_payload,
                tags=[service, "pattern_adapted", incident.get("incident_id", "")] if incident.get("incident_id") else [service, "pattern_adapted"],
                context=f"service: {service} | pattern_adapted_from: {top_match.get('tags') if top_match else 'memory'}",
            )

            elapsed = time.time() - start_time
            return {
                "incident_id": incident.get("incident_id"),
                "service": service,
                "path_taken": "pattern_adapted_path",
                "tag": "🧬 Pattern adapted from memory",
                "elapsed_seconds": round(elapsed, 3),
                "match_classification": match_classification,
                "top_score": top_match.get("scores") if top_match else None,
                "referenced_memory": top_match.get("tags") if top_match else [],
                "diagnosis": diagnosis,
                "retained_to_memory": True,
                "retain_response": {
                    "success": getattr(retain_res, "success", True),
                    "items_count": getattr(retain_res, "items_count", 1),
                },
                "instantly_resolved_counter": self.instantly_resolved_count,
                "pattern_adapted_counter": self.pattern_adapted_count,
            }

        # 3. SLOW PATH: No Match Found (Reason from scratch & Retain to memory)
        else:
            self.slow_diagnosed_count += 1
            diagnosis = self.llm.reason_from_scratch(incident)

            # Auto-retain the resolution to Hindsight memory so it remembers for next time
            retain_payload = {
                "incident_id": incident.get("incident_id"),
                "service": service,
                "symptom": symptom,
                "error_signature": error_sig,
                "root_cause": diagnosis.get("root_cause", ""),
                "fix_applied": diagnosis.get("recommended_fix", ""),
                "timestamp": incident.get("timestamp", ""),
            }

            retain_res = self.hindsight.retain_incident(
                incident=retain_payload,
                tags=[service, incident.get("incident_id", "")] if incident.get("incident_id") else [service],
                context=f"service: {service} | error: {error_sig}",
            )

            elapsed = time.time() - start_time
            return {
                "incident_id": incident.get("incident_id"),
                "service": service,
                "path_taken": "slow_path",
                "tag": "🔍 New diagnosis",
                "elapsed_seconds": round(elapsed, 3),
                "match_classification": match_classification,
                "top_score": top_match.get("scores") if top_match else None,
                "diagnosis": diagnosis,
                "retained_to_memory": True,
                "retain_response": {
                    "success": getattr(retain_res, "success", True),
                    "items_count": getattr(retain_res, "items_count", 1),
                },
                "instantly_resolved_counter": self.instantly_resolved_count,
            }

