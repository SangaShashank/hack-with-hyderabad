import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()


class HindsightMemoryClient:
    """Wrapper around Hindsight client for incident memory retain and recall."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        bank_id: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("HINDSIGHT_API_KEY")
        if not self.api_key:
            raise ValueError("HINDSIGHT_API_KEY must be provided or set in environment variables (.env).")
        
        self.base_url = base_url or os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
        self.bank_id = bank_id or os.getenv("HINDSIGHT_BANK_ID", "incident-response-bank")

        self.client = Hindsight(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def format_incident_content(self, incident: Dict[str, Any]) -> str:
        """Format a structured incident record into detailed content for memory retention."""
        return (
            f"Incident ID: {incident.get('incident_id', 'UNKNOWN')}\n"
            f"Service: {incident.get('service', 'UNKNOWN')}\n"
            f"Symptom: {incident.get('symptom', 'UNKNOWN')}\n"
            f"Error Signature: {incident.get('error_signature', 'UNKNOWN')}\n"
            f"Root Cause: {incident.get('root_cause', 'UNKNOWN')}\n"
            f"Fix Applied: {incident.get('fix_applied', 'UNKNOWN')}\n"
            f"Timestamp: {incident.get('timestamp', '')}\n"
            f"Resolution Summary: Service {incident.get('service')} failed with error '{incident.get('error_signature')}'. "
            f"Root cause was determined as: {incident.get('root_cause')}. "
            f"The effective fix applied was: {incident.get('fix_applied')}."
        )

    def retain_incident(
        self,
        incident: Dict[str, Any],
        tags: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> Any:
        """Retain a single incident record into Hindsight memory."""
        content = self.format_incident_content(incident)
        doc_id = incident.get("incident_id")
        service = incident.get("service", "")
        
        default_tags = [service] if service else []
        if doc_id:
            default_tags.append(doc_id)
        if tags:
            default_tags.extend(tags)

        context_str = context or f"service: {service} | incident_id: {doc_id}"

        response = self.client.retain(
            bank_id=self.bank_id,
            content=content,
            context=context_str,
            document_id=doc_id,
            tags=list(set(default_tags)) if default_tags else None
        )
        return response

    def close(self):
        """Close underlying client session."""
        if hasattr(self.client, "close"):
            try:
                self.client.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def recall(
        self,
        query: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        budget: str = "mid",
        max_tokens: int = 4096,
    ) -> Any:
        """Recall relevant incident memories from Hindsight memory bank."""
        try:
            response = self.client.recall(
                bank_id=self.bank_id,
                query=query,
                tags=tags,
                budget=budget,
                max_tokens=max_tokens,
            )
            return response
        except Exception as e:
            # If bank has not been initialized yet (e.g. brand new bank), treat as empty memory
            if "not found" in str(e).lower() or getattr(e, "status", None) == 404:
                from hindsight_client import RecallResponse
                return RecallResponse(results=[])
            raise e


    def recall_incident_matches(
        self,
        query: str,
        min_semantic_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Recall memories and return parsed items with scores and tags."""
        response = self.recall(query=query)
        matches = []
        for res in getattr(response, "results", []):
            raw_scores = getattr(res, "scores", None)
            if hasattr(raw_scores, "model_dump"):
                scores_dict = raw_scores.model_dump()
            elif hasattr(raw_scores, "dict"):
                scores_dict = raw_scores.dict()
            elif isinstance(raw_scores, dict):
                scores_dict = raw_scores
            else:
                scores_dict = {
                    "final": getattr(raw_scores, "final", None),
                    "semantic": getattr(raw_scores, "semantic", None),
                    "reranker": getattr(raw_scores, "reranker", None),
                    "keyword": getattr(raw_scores, "keyword", None),
                } if raw_scores else {}

            item = {
                "id": getattr(res, "id", None),
                "type": getattr(res, "type", None),
                "text": getattr(res, "text", ""),
                "tags": getattr(res, "tags", []) or [],
                "scores": scores_dict,
            }
            matches.append(item)
        return matches


