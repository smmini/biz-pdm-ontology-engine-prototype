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


_singleton_instance: Optional["MappingStore"] = None
MAPPING_CACHE_PATH = "ontology/mapping_cache.json"

def get_mapping_store() -> "MappingStore":
    """
    프로세스 전역에서 공유되는 MappingStore 싱글톤을 반환한다.
    최초 호출 시에만 파일에서 로드하고, 이후에는 메모리 상의 동일 인스턴스를 반환한다.
    """
    global _singleton_instance
    if _singleton_instance is None:
        _singleton_instance = MappingStore()
        _singleton_instance.load_from_file(MAPPING_CACHE_PATH)
    return _singleton_instance

def reload_mapping_store() -> "MappingStore":
    """캐시 파일이 외부에서 갱신된 뒤 강제로 다시 로드해야 할 때 사용."""
    global _singleton_instance
    _singleton_instance = MappingStore()
    _singleton_instance.load_from_file(MAPPING_CACHE_PATH)
    return _singleton_instance

