import json
import os
from pydantic import BaseModel
from typing import Dict, Optional

class MappingRecord(BaseModel):
    source_field: str
    target_ontology: str
    source: str         # 매핑 근거의 출처: column_name / equipment_manual / erp_metadata / user_confirmed
    confidence: float   # 0.0 ~ 1.0
    status: str         # "pending", "confirmed" 등

class MappingStore:
    def __init__(self):
        self._mappings: Dict[str, MappingRecord] = {}

    def add_mapping(self, record: MappingRecord):
        self._mappings[record.source_field] = record

    def get_mapping(self, source_field: str) -> Optional[MappingRecord]:
        return self._mappings.get(source_field)

    def confirm_mapping(self, source_field: str):
        if source_field in self._mappings:
            self._mappings[source_field].status = "confirmed"
            self._mappings[source_field].source = "user_confirmed"
            self._mappings[source_field].confidence = 1.0

    def get_all(self):
        return self._mappings

    def load_from_file(self, path: str):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for source_field, v in data.items():
            self._mappings[source_field] = MappingRecord(source_field=source_field, **v)

    def save_to_file(self, path: str):
        data = {
            k: {
                "target_ontology": v.target_ontology,
                "source": v.source,
                "confidence": v.confidence,
                "status": v.status,
            }
            for k, v in self._mappings.items()
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
