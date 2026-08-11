import json
import os
import logging
import pandas as pd
from systems.generator.ontology_mapping.ontology_mapping_store import get_mapping_store
from systems.generator.feature.feature_builder import load_catalog, build_features
from systems.generator.model.model_registry import REGISTERED_MODELS

logger = logging.getLogger(__name__)

_model_cache: dict[str, tuple[float, object]] = {}  # name -> (mtime, model_instance)

def _get_or_load_model(name: str, path: str):
    if not os.path.exists(path):
        logger.warning(f"[ModelCache] Model file path '{path}' does not exist.")
        return None
        
    mtime = os.path.getmtime(path)
    cached = _model_cache.get(name)
    if cached and cached[0] == mtime:
        logger.debug(f"[ModelCache] Reusing in-memory instance for model '{name}' (mtime: {mtime})")
        return cached[1]
    
    cls = REGISTERED_MODELS.get(name)
    if not cls:
        logger.warning(f"[ModelCache] Model '{name}' is not in REGISTERED_MODELS.")
        return None
        
    logger.info(f"[ModelCache] Loading model '{name}' from disk path '{path}' (mtime: {mtime})...")
    model = cls()
    model.load(path)
    _model_cache[name] = (mtime, model)
    return model


def predict_all(new_rows: list[dict], store_dir: str = "models_store"):
    """
    new_rows: 최근 N건의 telemetry 레코드 (dict 리스트)
    """
    registry_path = os.path.join(store_dir, "registry.json")
    if not os.path.exists(registry_path):
        raise ValueError("모델 레지스트리를 찾을 수 없습니다. 먼저 학습(/api/train)을 진행해주세요.")
        
    with open(registry_path, "r", encoding="utf-8") as f:
        registry_meta = json.load(f)

    store = get_mapping_store()

    catalog = load_catalog()
    df = pd.DataFrame(new_rows)
    
    # Feature 생성 (rolling_mean 등을 위해 여러 행 필요)
    features = build_features(df, store, catalog)

    if features.empty:
        raise ValueError(f"Feature 계산에 필요한 최소 행 수가 부족합니다 (입력 {len(df)}건). 더 많은 과거 데이터를 함께 전달해주세요.")

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    predictions = {}
    for name, meta in registry_meta["models"].items():
        model = _get_or_load_model(name, meta["path"])
        if not model:
            continue
            
        # 모델 예측 (가장 최근 1행만 SHAP 계산하여 반환)
        pred_output = model.predict(features)
        pred_output.prediction_timestamp = now_iso
        predictions[name] = pred_output.model_dump()

    return predictions

