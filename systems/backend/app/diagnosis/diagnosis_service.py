import json
import os
import logging
import pandas as pd
from systems.generator.ontology_mapping.mapping_store import MappingStore
from systems.generator.feature.builder import load_catalog, build_features
from models.registry import REGISTERED_MODELS

logger = logging.getLogger(__name__)

def predict_all(new_rows: list[dict], store_dir: str = "models_store"):
    """
    new_rows: 최근 N건의 telemetry 레코드 (dict 리스트)
    """
    registry_path = os.path.join(store_dir, "registry.json")
    if not os.path.exists(registry_path):
        raise ValueError("모델 레지스트리를 찾을 수 없습니다. 먼저 학습(/api/train)을 진행해주세요.")
        
    with open(registry_path, "r", encoding="utf-8") as f:
        registry_meta = json.load(f)

    store = MappingStore()
    cache_path = "ontology/mapping_cache.json"
    if not os.path.exists(cache_path):
        raise ValueError("매핑 캐시를 찾을 수 없습니다. 먼저 학습을 진행해주세요.")
        
    store.load_from_file(cache_path)   # Agent 재호출 없이 캐시만 사용

    catalog = load_catalog()
    df = pd.DataFrame(new_rows)
    
    # Feature 생성 (rolling_mean 등을 위해 여러 행 필요)
    features = build_features(df, store, catalog)

    if features.empty:
        raise ValueError(f"Feature 계산에 필요한 최소 행 수가 부족합니다 (입력 {len(df)}건). 더 많은 과거 데이터를 함께 전달해주세요.")

    predictions = {}
    for name, meta in registry_meta["models"].items():
        cls = REGISTERED_MODELS.get(name)
        if not cls:
            logger.warning(f"Model '{name}' is in registry but not registered in codebase. Skipping.")
            continue
            
        model = cls()
        model.load(meta["path"])
        # 모델 예측 (가장 최근 1행만 SHAP 계산하여 반환)
        pred_output = model.predict(features)
        predictions[name] = pred_output.model_dump()

    return predictions
