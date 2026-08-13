import json
import logging
import os
import yaml
from systems.generator.ontology_mapping.ontology_mapping_store import MappingStore, MappingRecord, MAPPING_CACHE_PATH, get_mapping_store
from systems.generator.generator_llm_client import call_llm

logger = logging.getLogger(__name__)

DEFAULT_ONTOLOGY_NODES = [
    "Voltage", "Rotation", "Pressure", "Vibration",
    "AirTemperature", "ProcessTemperature", "RotationalSpeed", "Torque", "ToolWear",
    "Equipment", "Timestamp", "ErrorEvent", "FailureEvent", "MaintenanceEvent", "Unknown"
]

def load_catalog_nodes() -> list:
    catalog_path = os.path.join(os.path.dirname(__file__), "..", "feature", "catalog.yaml")
    if not os.path.exists(catalog_path):
        catalog_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "feature_catalog", "catalog.yaml")
        
    nodes = list(DEFAULT_ONTOLOGY_NODES)
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                cat_features = yaml.safe_load(f).get("features", {})
                for node in cat_features.keys():
                    if node not in nodes:
                        nodes.append(node)
        except Exception as e:
            logger.warning(f"[MappingAgent] Failed to load catalog.yaml for dynamic prompt: {e}")
    return nodes

from systems.generator.extraction.extraction_profiler import load_family_registry

def build_system_prompt(nodes: list) -> str:
    nodes_str = ", ".join(nodes)
    return (
        "당신은 제조 데이터 온톨로지 매핑 전문가입니다.\n"
        "주어진 컬럼명, 파일 역할 맥락, 샘플 값을 보고 아래 온톨로지 노드 목록 중 가장 적합한 하나를 선택하여 매핑하세요:\n"
        f"{nodes_str}\n\n"
        "반드시 JSON 형식으로만 응답하세요: {\"ontology_node\": \"...\", \"confidence\": 0.0~1.0, \"reason\": \"...\"}"
    )

def map_column(column_name: str, sample_values: list, store: MappingStore, file_metadata: dict | None = None) -> MappingRecord:
    logger.info(f"[MappingAgent] Agent processing column: '{column_name}' with samples: {sample_values[:3]}")
    
    nodes = load_catalog_nodes()
    base_prompt = build_system_prompt(nodes)
    
    context = ""
    if file_metadata:
        role = file_metadata.get("role", "unknown")
        desc = file_metadata.get("description", "")
        notes = file_metadata.get("column_notes", {}).get(column_name, "")
        context = (
            f"[파일 맥락 정보]\n"
            f"- 파일 설명: {desc}\n"
            f"- 파일 역할 (Role): {role}\n"
        )
        if notes:
            context += f"- 컬럼 비고: {notes}\n"
        context += "\n"

    system_prompt = context + base_prompt
    prompt = f"컬럼명: {column_name}\n샘플 값: {sample_values[:5]}"
    
    try:
        raw = call_llm(prompt, system=system_prompt)
        logger.debug(f"[MappingAgent] LLM raw response for '{column_name}': {raw}")
        parsed = json.loads(raw)
        target = parsed.get("ontology_node", "Unknown")
        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "")
    except Exception as e:
        logger.warning(f"[MappingAgent] LLM mapping inference failed for '{column_name}': {e}. Falling back to Unknown.")
        target = "Unknown"
        confidence = 0.0
        reason = f"Error during inference: {e}"

    logger.info(f"[MappingAgent] Agent mapped '{column_name}' -> '{target}' (confidence: {confidence:.2f}) Reason: {reason}")

    record = MappingRecord(
        source_field=column_name,
        target_ontology=target,
        source="mapping_agent",
        confidence=confidence,
        status="pending" if confidence < 0.7 else "auto_mapped",
    )
    store.add_mapping(record)
    return record

def map_all_sources(sources: dict, store: MappingStore = None) -> MappingStore:
    logger.info("[MappingAgent] Starting agent-based mapping for all sources (with Stage 0 file metadata context)...")
    if store is None:
        store = get_mapping_store()

    family_registry = load_family_registry()

    updated = False
    for source_key, df in sources.items():
        # source_key 매칭 파일 메타데이터 조회
        matched_filename = next(
            (fname for fname in family_registry if os.path.splitext(fname)[0] == source_key), None
        )
        file_meta = family_registry.get(matched_filename) if matched_filename else None

        # Confidence 게이팅: status가 pending이거나 confidence < 0.7 이면 이 파일 매핑은 건너뜀
        if file_meta and (file_meta.get("status") == "pending" or float(file_meta.get("confidence", 1.0)) < 0.7):
            logger.warning(f"[MappingAgent] Skipping mapping for source dataset '{source_key}' because file metadata status is '{file_meta.get('status')}' (confidence={file_meta.get('confidence')}).")
            continue

        logger.info(f"[MappingAgent] Mapping source dataset: '{source_key}' ({len(df.columns)} columns) with metadata role='{file_meta.get('role') if file_meta else 'none'}'")
        for col in df.columns:
            if store.get_mapping(col) is not None:
                continue

            sample = df[col].dropna().astype(str).head(5).tolist()
            map_column(col, sample, store, file_metadata=file_meta)
            updated = True
    
    if updated:
        store.save_to_file(MAPPING_CACHE_PATH)
        logger.info(f"[MappingAgent] Updated mapping file saved to '{MAPPING_CACHE_PATH}'.")

    logger.info(f"[MappingAgent] Completed agent mapping. Total mappings in store: {len(store.get_all())}")
    return store
