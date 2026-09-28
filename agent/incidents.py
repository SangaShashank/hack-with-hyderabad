import os
import json
from typing import Any, Dict, List, Optional


class IncidentDataset:
    """Loader and manager for the synthetic microservice incident dataset."""

    DEFAULT_DATA_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "incidents.json")
    )

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.incidents = self._load_data()

    def _load_data(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Incident dataset not found at {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_all(self) -> List[Dict[str, Any]]:
        return self.incidents

    def get_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        for inc in self.incidents:
            if inc.get("incident_id") == incident_id:
                return inc
        return None

    def get_by_failure_family(self, family: str) -> List[Dict[str, Any]]:
        return [inc for inc in self.incidents if inc.get("failure_family") == family]

    def get_demo_sequence(self) -> List[Dict[str, Any]]:
        """
        Returns the curated 5-incident demo sequence:
        1. Incident #1 (payments-api DB pool exhaustion) - Slow path (reason from scratch)
        2. Incident #2 (auth-service memory leak) - Unrelated family, Slow path (learns new family)
        3. Incident #3 (orders-api DB pool exhaustion) - Cross-service variant of #1, Pattern Adaptation
        4. Incident #4 (payments-api DB pool recurrence) - Exact recurrence of #1, Fast path (Instant Recall)
        5. Incident #5 (auth-service memory leak recurrence) - Exact recurrence of #2, Fast path (Instant Recall)
        """
        seq_ids = ["INC-0001", "INC-0002", "INC-0006", "INC-0011", "INC-0012"]
        result = []
        for inc_id in seq_ids:
            inc = self.get_by_id(inc_id)
            if inc:
                result.append(inc)
        return result
