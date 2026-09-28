import os
import sys
import time
import re
import uuid
import datetime
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

    def _extract_from_recalled_memory(
        self,
        incident: Dict[str, Any],
        top_match: Optional[Dict[str, Any]],
        prompt_string: str,
        matches: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to resolve a recurring incident directly from structured Hindsight memory
        without invoking Groq LLM unnecessarily.
        """
        if not top_match and not matches:
            return None

        combined_text = prompt_string + "\n" + "\n".join(m.get("text", "") for m in matches[:3])

        rc_patterns = [
            r"(?:Root cause was determined as:\s*|Root Cause:\s*)([^\.\n]+(?:\.[^\.\n]+)?)",
            r"(?:root cause.*?:\s*)([^\.\n]+(?:\.[^\.\n]+)?)",
        ]
        fix_patterns = [
            r"(?:The effective fix applied was:\s*|Fix Applied:\s*|proven_fix:\s*|recommended_fix:\s*)([^\.\n]+(?:\.[^\.\n]+)?)",
            r"(?:fix applied.*?:\s*)([^\.\n]+(?:\.[^\.\n]+)?)",
        ]

        root_cause = None
        for pat in rc_patterns:
            m = re.search(pat, combined_text, re.IGNORECASE)
            if m:
                root_cause = m.group(1).strip()
                break

        fix = None
        for pat in fix_patterns:
            m = re.search(pat, combined_text, re.IGNORECASE)
            if m:
                fix = m.group(1).strip()
                break

        if root_cause and fix:
            tags = top_match.get("tags", []) if top_match else []
            ref_id = next((t for t in tags if t.startswith("INC-") or t.startswith("USER-")), None)
            if not ref_id and tags:
                ref_id = tags[0]
            if not ref_id:
                ref_id = "Organizational Incident Memory"

            service = incident.get("service", "unknown-service")
            error_sig = incident.get("error_signature", "")
            return {
                "source": "memory",
                "path": "fast_path",
                "confidence": "high",
                "referenced_incident": ref_id,
                "headline": f"Seen this before in {service}: {error_sig[:50]}",
                "root_cause": root_cause,
                "proven_fix": fix,
                "prevention_advice": "Maintain configured resource limits, connection thresholds, and automated health checks.",
                "raw_llm_narrative": f"Incident pattern recognized from shared memory ({ref_id}). The root cause was identified as: '{root_cause}'. Verified remediation applied: '{fix}'.",
            }
        return None

    def handle_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming incident record through Hindsight memory and LLM.
        Supports both predefined synthetic incidents and operator-submitted incidents.
        """
        start_time = time.time()

        # Normalize incident fields
        incident_id = incident.get("incident_id")
        if not incident_id:
            ts_str = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            rand_tag = uuid.uuid4().hex[:6].upper()
            incident_id = f"USER-{ts_str}-{rand_tag}"
            incident["incident_id"] = incident_id

        service = incident.get("service", "unknown-service")
        error_sig = incident.get("error_signature", "")
        symptom = incident.get("symptom") or incident.get("symptoms", "")
        incident["symptom"] = symptom
        incident["symptoms"] = symptom

        timestamp = incident.get("timestamp")
        if not timestamp:
            timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            incident["timestamp"] = timestamp

        query = f"{service} {error_sig} {symptom}".strip()

        # Step A: Check Hindsight Memory Bank (Primary Service-Aware Query)
        raw_recall = self.hindsight.recall(query=query)
        matches = self.hindsight.recall_incident_matches(query=query, response=raw_recall)
        prompt_string = raw_recall.to_prompt_string()

        match_classification, top_match, relevant_matches = self.evaluate_memory_matches(matches, service)

        # Cross-service fallback recall: if primary recall returns no usable matches,
        # query by failure family (error signature + symptoms) without the service name
        if match_classification == "no_match":
            family_query = f"{error_sig} {symptom}".strip()
            if family_query and family_query != query:
                fb_raw_recall = self.hindsight.recall(query=family_query)
                fb_matches = self.hindsight.recall_incident_matches(query=family_query, response=fb_raw_recall)
                fb_classification, fb_top_match, fb_relevant = self.evaluate_memory_matches(fb_matches, service)
                if fb_classification != "no_match":
                    match_classification = fb_classification
                    top_match = fb_top_match
                    relevant_matches = fb_relevant
                    prompt_string = fb_raw_recall.to_prompt_string()

        # 1. FAST PATH: Strong Match in Memory (Exact recurrence)
        if match_classification == "strong_match":
            self.instantly_resolved_count += 1
            # Attempt instant resolution directly from recalled Hindsight memory first
            diagnosis = self._extract_from_recalled_memory(incident, top_match, prompt_string, relevant_matches)
            if not diagnosis:
                diagnosis = self.llm.synthesize_from_memory(
                    incident=incident,
                    recalled_memories_prompt=prompt_string,
                    recalled_records=relevant_matches,
                )
            elapsed = time.time() - start_time
            return {
                "incident_id": incident_id,
                "service": service,
                "error_signature": error_sig,
                "symptom": symptom,
                "timestamp": timestamp,
                "path_taken": "fast_path",
                "tag": "🧠 Recalled from memory",
                "elapsed_seconds": round(elapsed, 3),
                "match_classification": match_classification,
                "top_score": top_match.get("scores") if top_match else None,
                "referenced_memory": top_match.get("tags") if top_match else [],
                "diagnosis": diagnosis,
                "instantly_resolved_counter": self.instantly_resolved_count,
                "pattern_adapted_counter": self.pattern_adapted_count,
                "slow_diagnosed_counter": self.slow_diagnosed_count,
            }

        # 2. PATTERN ADAPTATION PATH: Partial Match across services / variants
        elif match_classification == "partial_match":
            self.pattern_adapted_count += 1
            diagnosis = self.llm.adapt_pattern_from_memory(
                incident=incident,
                recalled_memories_prompt=prompt_string,
                recalled_records=relevant_matches,
            )

            # Auto-retain adapted fix to Hindsight memory for this new service
            retain_payload = {
                "incident_id": incident_id,
                "service": service,
                "symptom": symptom,
                "error_signature": error_sig,
                "root_cause": diagnosis.get("pattern_explanation", ""),
                "fix_applied": diagnosis.get("adapted_fix", ""),
                "timestamp": timestamp,
            }
            retain_res = self.hindsight.retain_incident(
                incident=retain_payload,
                tags=[service, "pattern_adapted", incident_id] if incident_id else [service, "pattern_adapted"],
                context=f"service: {service} | pattern_adapted_from: {top_match.get('tags') if top_match else 'memory'}",
            )

            elapsed = time.time() - start_time
            return {
                "incident_id": incident_id,
                "service": service,
                "error_signature": error_sig,
                "symptom": symptom,
                "timestamp": timestamp,
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
                "slow_diagnosed_counter": self.slow_diagnosed_count,
            }

        # 3. SLOW PATH: No Match Found (Reason from scratch & Retain to memory)
        else:
            self.slow_diagnosed_count += 1
            diagnosis = self.llm.reason_from_scratch(incident)

            # Auto-retain the resolution to Hindsight memory so it remembers for next time
            retain_payload = {
                "incident_id": incident_id,
                "service": service,
                "symptom": symptom,
                "error_signature": error_sig,
                "root_cause": diagnosis.get("root_cause", ""),
                "fix_applied": diagnosis.get("recommended_fix", ""),
                "timestamp": timestamp,
            }

            retain_res = self.hindsight.retain_incident(
                incident=retain_payload,
                tags=[service, incident_id] if incident_id else [service],
                context=f"service: {service} | error: {error_sig}",
            )

            elapsed = time.time() - start_time
            return {
                "incident_id": incident_id,
                "service": service,
                "error_signature": error_sig,
                "symptom": symptom,
                "timestamp": timestamp,
                "path_taken": "slow_path",
                "tag": "🔍 New diagnosis",
                "elapsed_seconds": round(elapsed, 3),
                "match_classification": match_classification,
                "top_score": top_match.get("scores") if top_match else None,
                "referenced_memory": [],
                "diagnosis": diagnosis,
                "retained_to_memory": True,
                "retain_response": {
                    "success": getattr(retain_res, "success", True),
                    "items_count": getattr(retain_res, "items_count", 1),
                },
                "instantly_resolved_counter": self.instantly_resolved_count,
                "pattern_adapted_counter": self.pattern_adapted_count,
                "slow_diagnosed_counter": self.slow_diagnosed_count,
            }

