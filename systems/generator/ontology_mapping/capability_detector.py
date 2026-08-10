from systems.generator.ontology_mapping.mapping_store import MappingStore

def detect_capabilities(store: MappingStore) -> dict:
    """
    MappingStore에 저장된 target_ontology 필드들을 기반으로
    시스템이 실행 가능한 도메인 역량(Capability)을 감지합니다.
    """
    mapped_targets = {v.target_ontology for v in store.get_all().values()}
    
    capabilities = {
        "EquipmentMonitoring": "Equipment" in mapped_targets,
        "SensorAnalytics": any(t in mapped_targets for t in ["Voltage", "Rotation", "Pressure", "Vibration", "AirTemperature", "ProcessTemperature", "RotationalSpeed", "Torque", "ToolWear"]),
        "MaintenanceHistory": "MaintenanceEvent" in mapped_targets,
        "FailurePrediction": "FailureEvent" in mapped_targets,
        "ErrorTracking": "ErrorEvent" in mapped_targets,
    }
    return capabilities
