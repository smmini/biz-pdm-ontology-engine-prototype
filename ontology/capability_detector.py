import logging
from ontology.mapping_store import MappingStore

logger = logging.getLogger(__name__)

CAPABILITY_RULES = {
    "Sensor": ["Voltage", "RotationSpeed", "Pressure", "Vibration"],
    "Failure": ["FailureEvent", "ErrorEvent"],
    "Maintenance": ["MaintenanceEvent"],
    "Cost": ["CostData"],       # 이 데이터셋엔 없음 -> 자동으로 False가 되어야 함
    "Inventory": ["InventoryLevel"],  # 이 데이터셋엔 없음
}

def detect_capabilities(store: MappingStore) -> dict:
    logger.info("[CapabilityDetector] Starting capability detection based on mappings...")
    mapped_nodes = {r.target_ontology for r in store.get_all().values()}
    logger.info(f"[CapabilityDetector] Current mapped nodes: {mapped_nodes}")
    
    capabilities = {}
    for capability, required_nodes in CAPABILITY_RULES.items():
        is_active = any(node in mapped_nodes for node in required_nodes)
        capabilities[capability] = is_active
        logger.info(f"[CapabilityDetector] Capability '{capability}': {is_active} (Requires any of: {required_nodes})")
        
    return capabilities
