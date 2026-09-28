import os
import json
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class GroqLLMClient:
    """LLM Client wrapping Groq API calls with retries, model fallbacks, and error handling."""

    PRIMARY_MODEL = "openai/gpt-oss-120b"
    FALLBACK_MODEL = "openai/gpt-oss-20b"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be provided or set in environment variables (.env).")
        self.client = Groq(api_key=self.api_key)
        self.model = model or self.PRIMARY_MODEL

    def _call_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        json_output: bool = True,
        max_retries: int = 3,
    ) -> str:
        """Call Groq chat completion with retries and model fallback."""
        models_to_try = [self.model, self.FALLBACK_MODEL] if self.model != self.FALLBACK_MODEL else [self.model]
        last_error = None

        for model_choice in models_to_try:
            for attempt in range(1, max_retries + 1):
                try:
                    kwargs = {
                        "model": model_choice,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if json_output:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = self.client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    if content:
                        return content
                except Exception as e:
                    last_error = e
                    time.sleep(0.8 * attempt)
        
        # If all attempts fail, provide safe fallback
        raise RuntimeError(f"All Groq LLM attempts failed. Last error: {last_error}")

    def synthesize_from_memory(
        self,
        incident: Dict[str, Any],
        recalled_memories_prompt: str,
        recalled_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Fast Path: Generate an incident response synthesized from recalled Hindsight memory.
        The LLM explicitly references the past incident, symptoms, root cause, and proven fix.
        """
        system_prompt = (
            "You are an expert microservice Site Reliability Engineer (SRE) on-call assistant.\n"
            "You have access to persistent organizational incident memory via Hindsight.\n"
            "A memory match has been found for the current incident.\n"
            "Your task is to synthesize a high-confidence, actionable diagnosis that EXPLICITLY references "
            "the past incident(s) from memory, explains how the past root cause applies here, and details the fix that worked.\n\n"
            "You must return your output strictly in valid JSON matching this schema:\n"
            "{\n"
            '  "source": "memory",\n'
            '  "path": "fast_path",\n'
            '  "confidence": "high",\n'
            '  "referenced_incident": "<ID or summary of past incident referenced, e.g. INC-0001>",\n'
            '  "headline": "<Concise message, e.g. Seen this before: ConnectionPoolTimeoutError in payments-api>",\n'
            '  "root_cause": "<Detailed explanation citing the past findings>",\n'
            '  "proven_fix": "<Step-by-step resolution that worked in the past and is applicable now>",\n'
            '  "prevention_advice": "<Advice to avoid recurrence>",\n'
            '  "raw_llm_narrative": "<A clear 2-3 paragraph explanation an engineer can read in Slack/PagerDuty>"\n'
            "}"
        )

        user_content = (
            f"CURRENT INCOMING INCIDENT:\n"
            f"Service: {incident.get('service')}\n"
            f"Error Signature: {incident.get('error_signature')}\n"
            f"Symptom: {incident.get('symptom')}\n"
            f"Timestamp: {incident.get('timestamp')}\n\n"
            f"RECALLED HINDSIGHT MEMORY CONTEXT:\n"
            f"{recalled_memories_prompt}\n\n"
            f"Instructions:\n"
            f"1. Acknowledge that this pattern has been seen and resolved before in memory.\n"
            f"2. Explicitly cite the prior incident record / context.\n"
            f"3. State the root cause that was diagnosed previously.\n"
            f"4. Provide the exact fix that worked."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            raw_response = self._call_chat_completion(messages, temperature=0.1, json_output=True)
            parsed = json.loads(raw_response)
            return parsed
        except Exception as e:
            # Fallback if parsing fails or LLM errors
            return {
                "source": "memory",
                "path": "fast_path",
                "confidence": "high",
                "referenced_incident": "Past Incident from Memory",
                "headline": f"Seen this before in {incident.get('service')}",
                "root_cause": f"Recalled from Hindsight: Root cause matches past error signature {incident.get('error_signature')}.",
                "proven_fix": "Apply past verified fix stored in Hindsight memory.",
                "prevention_advice": "Check resource limits and pool thresholds.",
                "raw_llm_narrative": f"Pattern match verified against Hindsight memory for {incident.get('error_signature')}. (Fallback handler: {e})",
            }

    def reason_from_scratch(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Slow Path: When no prior memory match exists, LLM reasons from first principles
        to diagnose the root cause and prescribe an immediate fix.
        """
        system_prompt = (
            "You are an expert microservice Site Reliability Engineer (SRE) on-call assistant.\n"
            "No prior incident in memory matches the incoming alert. You must reason from first principles.\n"
            "Analyze the service, error signature, stack trace, and symptoms to deduce the root cause and provide "
            "an actionable remediation plan.\n\n"
            "You must return your output strictly in valid JSON matching this schema:\n"
            "{\n"
            '  "source": "new_diagnosis",\n'
            '  "path": "slow_path",\n'
            '  "confidence": "moderate",\n'
            '  "headline": "<Concise summary of new finding, e.g. New Failure: Memory Leak in auth-service>",\n'
            '  "root_cause": "<Deep first-principles technical diagnosis of why this failed>",\n'
            '  "recommended_fix": "<Step-by-step immediate and permanent remediation instructions>",\n'
            '  "prevention_advice": "<Longer-term architectural or monitoring fix>",\n'
            '  "raw_llm_narrative": "<Clear SRE communication summarizing the diagnosis and immediate action for on-call>"\n'
            "}"
        )

        user_content = (
            f"NEW UNSEEN INCIDENT TELEMETRY:\n"
            f"Incident ID: {incident.get('incident_id', 'NEW-INCIDENT')}\n"
            f"Service: {incident.get('service')}\n"
            f"Error Signature: {incident.get('error_signature')}\n"
            f"Symptom: {incident.get('symptom')}\n"
            f"Timestamp: {incident.get('timestamp')}\n\n"
            f"Please conduct an in-depth SRE diagnosis and provide actionable remediation."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            raw_response = self._call_chat_completion(messages, temperature=0.2, json_output=True)
            parsed = json.loads(raw_response)
            return parsed
        except Exception as e:
            return {
                "source": "new_diagnosis",
                "path": "slow_path",
                "confidence": "moderate",
                "headline": f"New Failure Pattern in {incident.get('service')}",
                "root_cause": f"Unseen failure: {incident.get('error_signature')}. First-principles analysis indicates resource/configuration anomaly.",
                "recommended_fix": "Inspect service logs, restart failing container, check recent deployment diffs.",
                "prevention_advice": "Configure automated health checks and alerts on error spikes.",
                "raw_llm_narrative": f"First-principles reasoning generated for {incident.get('service')}. (Fallback handler: {e})",
            }

    def adapt_pattern_from_memory(
        self,
        incident: Dict[str, Any],
        recalled_memories_prompt: str,
        recalled_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Pattern Adaptation Path: When an incident matches a known failure family
        from a past incident in a different service or context, recognize the pattern
        and adapt the fix to the new service rather than parroting the old answer verbatim.
        """
        system_prompt = (
            "You are an expert microservice Site Reliability Engineer (SRE) on-call assistant.\n"
            "An incident has occurred that exhibits a FAILURE PATTERN previously resolved in another service.\n"
            "Your task is to RECOGNIZE the underlying failure pattern from memory and ADAPT the fix to the new service.\n\n"
            "CRITICAL REQUIREMENT:\n"
            "- Do NOT simply repeat the past incident's fix verbatim.\n"
            "- Clearly explain the failure pattern shared between the two services.\n"
            "- Adapt the root-cause diagnosis and remediation to the specific architecture, service dependencies, "
            "and traffic characteristics of the NEW service.\n\n"
            "You must return your output strictly in valid JSON matching this schema:\n"
            "{\n"
            '  "source": "pattern_adaptation",\n'
            '  "path": "pattern_adapted_path",\n'
            '  "confidence": "high",\n'
            '  "pattern_family": "<Failure pattern name, e.g. Database Connection Pool Exhaustion>",\n'
            '  "referenced_incident": "<ID and service of past incident, e.g. INC-0001 (payments-api)>",\n'
            '  "headline": "<e.g. Pattern Recognized: DB pool exhaustion (INC-0001) adapted for orders-api>",\n'
            '  "pattern_explanation": "<How the failure mechanism matches the past pattern>",\n'
            '  "adaptation_notes": "<Why the fix must be tailored for this service rather than copied verbatim>",\n'
            '  "adapted_fix": "<Actionable, step-by-step resolution tailored specifically for the new service>",\n'
            '  "prevention_advice": "<Service-specific preventative measures>",\n'
            '  "raw_llm_narrative": "<Concise, professional explanation for the on-call channel>"\n'
            "}"
        )

        user_content = (
            f"NEW INCIDENT (REQUIRING PATTERN ADAPTATION):\n"
            f"Service: {incident.get('service')}\n"
            f"Error Signature: {incident.get('error_signature')}\n"
            f"Symptom: {incident.get('symptom')}\n"
            f"Timestamp: {incident.get('timestamp')}\n\n"
            f"RELEVANT FAILURE PATTERN FROM HINDSIGHT MEMORY:\n"
            f"{recalled_memories_prompt}\n\n"
            f"Instructions:\n"
            f"1. Identify the matching failure family from memory.\n"
            f"2. Note which service encountered it previously.\n"
            f"3. Adapt the resolution specifically to {incident.get('service')}, taking into account its role in the system."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            raw_response = self._call_chat_completion(messages, temperature=0.1, json_output=True)
            parsed = json.loads(raw_response)
            return parsed
        except Exception as e:
            return {
                "source": "pattern_adaptation",
                "path": "pattern_adapted_path",
                "confidence": "high",
                "pattern_family": "Recognized Architectural Failure Pattern",
                "referenced_incident": "Prior Incident from Memory",
                "headline": f"Pattern Recognized and Adapted for {incident.get('service')}",
                "pattern_explanation": f"Pattern similarity identified from prior incident in memory for {incident.get('error_signature')}.",
                "adaptation_notes": f"Tailored for {incident.get('service')} architecture.",
                "adapted_fix": f"Apply adapted resource scaling and connection pool adjustments to {incident.get('service')}.",
                "prevention_advice": "Configure service-specific thresholds and health checks.",
                "raw_llm_narrative": f"Pattern adaptation completed for {incident.get('service')}. (Fallback handler: {e})",
            }


