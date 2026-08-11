import json
import logging
import os
import yaml
from systems.generator.ontology_mapping.mapping_store import MappingStore, MappingRecord, MAPPING_CACHE_PATH, get_mapping_store
from systems.generator.infrastructure.llm.openai_client import call_llm

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

def build_system_prompt(nodes: list) -> str:
    nodes_str = ", ".join(nodes)
    return (
        "당신은 제조 데이터 온톨로지 매핑 전문가입니다.\n"
        "주어진 컬럼명과 샘플 값을 보고, 아래 온톨로지 노드 목록 중 가장 적합한 하나를 선택하여 매핑하세요:\n"
        f"{nodes_str}\n\n"
        "반드시 JSON 형식으로만 응답하세요: {\"ontology_node\": \"...\", \"confidence\": 0.0~1.0, \"reason\": \"...\"}"
    )

def map_column(column_name: str, sample_values: list, store: MappingStore) -> MappingRecord:
    logger.info(f"[MappingAgent] Agent processing column: '{column_name}' with samples: {sample_values[:3]}")
    
    nodes = load_catalog_nodes()
    system_prompt = build_system_prompt(nodes)
    
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
    logger.info("[MappingAgent] Starting agent-based mapping for all sources...")
    if store is None:
        store = get_mapping_store()
    
    if os.path.exists(MAPPING_CACHE_PATH):
        store.load_from_file(MAPPING_CACHE_PATH)
        logger.info(f"[MappingAgent] Loaded {len(store.get_all())} existing mappings from '{MAPPING_CACHE_PATH}'.")

    updated = False
    for source_key, df in sources.items():
        logger.info(f"[MappingAgent] Mapping source dataset: '{source_key}' ({len(df.columns)} columns)")
        for col in df.columns:
            if store.get_mapping(col) is not None:
                continue

            sample = df[col].dropna().astype(str).head(5).tolist()
            map_column(col, sample, store)
            updated = True
    
    if updated:
        store.save_to_file(MAPPING_CACHE_PATH)
        logger.info(f"[MappingAgent] Updated mapping file saved to '{MAPPING_CACHE_PATH}'.")

    logger.info(f"[MappingAgent] Completed agent mapping. Total mappings in store: {len(store.get_all())}")
    return store
