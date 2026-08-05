import json
import logging
from ontology.mapping_store import MappingStore, MappingRecord
from llm_provider.openai_client import call_llm

logger = logging.getLogger(__name__)

MAPPING_CACHE_PATH = "ontology/mapping_cache.json"

RULE_BASED_DICT = {
    "volt": "Voltage",
    "rotate": "RotationSpeed",
    "pressure": "Pressure",
    "vibration": "Vibration",
    "errorid": "ErrorEvent",
    "failure": "FailureEvent",
    "comp": "MaintenanceEvent",
    "machineid": "Equipment",
}

SYSTEM_PROMPT = """당신은 제조 데이터 온톨로지 매핑 전문가입니다.
주어진 컬럼명과 샘플 값을 보고, 아래 온톨로지 노드 중 가장 적합한 것 하나를 고르세요:
Voltage, RotationSpeed, Pressure, Vibration, ErrorEvent, FailureEvent, MaintenanceEvent, Equipment, Unknown

반드시 JSON으로만 답하세요: {"ontology_node": "...", "confidence": 0.0~1.0, "reason": "..."}
"""

def map_column(column_name: str, sample_values: list, store: MappingStore) -> MappingRecord:
    logger.info(f"[MappingAgent] Processing column: '{column_name}' with sample values: {sample_values[:3]}")
    key = column_name.strip().lower()

    # 1) 규칙 기반 우선
    if key in RULE_BASED_DICT:
        logger.info(f"[MappingAgent] Column '{column_name}' matched rule-based dict -> {RULE_BASED_DICT[key]}")
        record = MappingRecord(
            source_field=column_name,
            target_ontology=RULE_BASED_DICT[key],
            source="column_name",
            confidence=0.95,
            status="confirmed",
        )
        store.add_mapping(record)
        return record

    # 2) LLM 기반 추론 (사전에 없는 컬럼만)
    logger.info(f"[MappingAgent] Column '{column_name}' not in rules. Requesting LLM inference...")
    prompt = f"컬럼명: {column_name}\n샘플 값: {sample_values[:5]}"
    raw = call_llm(prompt, system=SYSTEM_PROMPT)
    logger.debug(f"[MappingAgent] LLM raw response for '{column_name}': {raw}")
    
    parsed = json.loads(raw)
    target = parsed.get("ontology_node", "Unknown")
    confidence = float(parsed.get("confidence", 0.5))
    reason = parsed.get("reason", "")
    
    logger.info(f"[MappingAgent] LLM mapped '{column_name}' -> {target} (confidence: {confidence}) Reason: {reason}")

    record = MappingRecord(
        source_field=column_name,
        target_ontology=target,
        source="llm_inference",
        confidence=confidence,
        status="pending" if confidence < 0.7 else "auto_mapped",
    )
    store.add_mapping(record)
    return record

def map_all_sources(sources: dict, store: MappingStore) -> MappingStore:
    """sources: mcp_tools.loader.load_all_sources()의 결과"""
    logger.info("[MappingAgent] Starting to map all sources...")
    
    # 1) 캐시 먼저 로드
    store.load_from_file(MAPPING_CACHE_PATH)
    logger.info(f"[MappingAgent] Loaded {len(store.get_all())} mappings from cache.")

    updated = False
    for source_key, df in sources.items():
        logger.info(f"[MappingAgent] Mapping source dataset: '{source_key}' ({len(df.columns)} columns)")
        for col in df.columns:
            key = col.strip().lower()
            if store.get_mapping(col) is not None:
                continue # 2) 이미 캐시/규칙에 있으면 스킵 (LLM 호출 없음)

            # 3) 캐시에도 없는 완전히 새로운 컬럼일 때만 규칙→LLM 순으로 처리
            sample = df[col].dropna().astype(str).head(5).tolist()
            map_column(col, sample, store)
            updated = True
    
    if updated:
        store.save_to_file(MAPPING_CACHE_PATH) # 4) 새로 추가된 것만 있으면 캐시 갱신
        logger.info("[MappingAgent] Cache file updated.")

    logger.info(f"[MappingAgent] Completed mapping. Total mappings in store: {len(store.get_all())}")
    return store
