import os
import json
import logging
from datetime import datetime

from systems.generator.extraction.loader import load_all_sources
from systems.generator.ontology_mapping.mapping_store import get_mapping_store, reload_mapping_store
from systems.generator.ontology_mapping.mapping_agent import map_all_sources
from systems.generator.ontology_mapping.capability_detector import detect_capabilities
from systems.generator.feature.builder import load_catalog, build_features, save_features_npy
from systems.generator.feature.label_builder import build_labels
from systems.generator.model.model_registry import REGISTERED_MODELS

logger = logging.getLogger(__name__)

from collections import defaultdict
from systems.generator.extraction.source_family import load_family_registry

def _select_training_pair(sources: dict) -> tuple[str, str, str, str | None, str | None]:
    """
    같은 family_id(동일 id/time 컬럼 스키마)에 속한 파일들 중에서만
    telemetry_key와 failures_key를 함께 찾는다. 서로 다른 계열이 섞이지 않는다.
    """
    registry = load_family_registry()
    by_family: dict[str, list[str]] = defaultdict(list)
    for key in sources:
        matched_filename = next(
            (fname for fname in registry if os.path.splitext(fname)[0] == key), None
        )
        family_id = registry.get(matched_filename, {}).get("family_id", "unknown") if matched_filename else "unknown"
        by_family[family_id].append(key)

    for family_id, keys in by_family.items():
        failures_keys = [k for k in keys if "failure" in k.lower()]
        if not failures_keys:
            continue
        for fail_k in failures_keys:
            prefix = fail_k.lower().split("_")[0]
            matched_telemetry = next((k for k in keys if k != fail_k and prefix in k.lower() and any(sub in k.lower() for sub in ("telemetry", "sensor", "observation"))), None)
            if not matched_telemetry:
                matched_telemetry = next((k for k in keys if k != fail_k and any(sub in k.lower() for sub in ("telemetry", "sensor", "observation"))), None)
            
            if matched_telemetry:
                telemetry_key = matched_telemetry
                failures_key = fail_k
                sample_filename = next((fname for fname in registry if os.path.splitext(fname)[0] == telemetry_key), None)
                id_col = registry.get(sample_filename, {}).get("id_col") if sample_filename else None
                time_col = registry.get(sample_filename, {}).get("time_col") if sample_filename else None
                logger.info(f"[TrainAll] Selected matching family '{family_id}': telemetry='{telemetry_key}', failures='{failures_key}' (id_col='{id_col}', time_col='{time_col}')")
                return telemetry_key, failures_key, family_id, id_col, time_col

    raise ValueError(
        "telemetry 데이터와 failure 라벨이 같은 계열(동일 id/time 컬럼 스키마)로 "
        "함께 존재하는 파일 조합을 찾지 못했습니다. data/ 구성을 확인해주세요."
    )

def train_all(data_dir: str = "data", store_dir: str = "models_store", force_reanalyze: bool = False):
    logger.info("========================================")
    logger.info(f"🚀 RUNNING TRAINING PIPELINE (v3): Data Directory = '{data_dir}', force_reanalyze = {force_reanalyze}")
    logger.info("========================================")
    
    logger.info(">>> STEP 1: PARSE & EXTRACT SOURCES (Extraction Agent)")
    sources = load_all_sources(data_dir, force_reanalyze=force_reanalyze)

    logger.info(">>> STEP 2: ONTOLOGY MAPPING")
    store = get_mapping_store()
    map_all_sources(sources, store)
    reload_mapping_store()
    
    logger.info(">>> STEP 3: CAPABILITY DETECTION")
    capabilities = detect_capabilities(store)

    logger.info(">>> STEP 4: DYNAMIC FAMILY MATCHING & FEATURE EXTRACTION")
    telemetry_key, failures_key, family_id, id_col, time_col = _select_training_pair(sources)
    catalog = load_catalog()
    features = build_features(sources[telemetry_key], store, catalog)
    save_features_npy(features, "data_preprocessed/features", telemetry_key)

    logger.info(">>> STEP 5: LABELING")
    labeled = build_labels(features, sources[failures_key])
    train_positive_rate = float(labeled["label"].mean())
    logger.info(f"Training dataset positive rate for family '{family_id}': {train_positive_rate:.4f}")

    logger.info(">>> STEP 6: TRAIN & SAVE MODELS")
    results = {}
    for name, cls in REGISTERED_MODELS.items():
        logger.info(f"Training model: {name}")
        model = cls()
        model.train(labeled, target_col="label", id_col=id_col, time_col=time_col)

        os.makedirs(os.path.join(store_dir, name), exist_ok=True)
        model_path = os.path.join(store_dir, name, "model.joblib")
        model.save(model_path)
        logger.info(f"Saved {name} to {model_path}")

        results[name] = {
            "path": model_path,
            "train_positive_rate": train_positive_rate,
        }

    logger.info(">>> STEP 7: SAVE REGISTRY METADATA")
    exclude = set(filter(None, ["datetime", "observed_at", "machineID", "asset_id", "label", id_col, time_col]))
    feature_cols = [c for c in labeled.columns if c not in exclude]
    registry_meta = {
        "trained_at": datetime.utcnow().isoformat(),
        "family_id": family_id,
        "source_telemetry_key": telemetry_key,
        "id_col": id_col,
        "time_col": time_col,
        "feature_cols": feature_cols,
        "models": results,
    }
    
    os.makedirs(store_dir, exist_ok=True)
    registry_path = os.path.join(store_dir, "registry.json")
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_meta, f, ensure_ascii=False, indent=2)
    logger.info(f"Registry metadata saved to: {registry_path}")

    logger.info("========================================")
    logger.info("✅ TRAINING PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("========================================")

    return {
        "capabilities": capabilities, 
        "mappings": {
            k: {
                "source_field": v.source_field,
                "target_ontology": v.target_ontology,
                "source": v.source,
                "confidence": v.confidence,
                "status": v.status
            } for k, v in store.get_all().items()
        }, 
        "registry": registry_meta
    }
