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

def _get_file_meta(sources_key: str, registry: dict) -> dict:
    matched = next(
        (fname for fname in registry if os.path.splitext(fname)[0] == sources_key), None
    )
    return registry.get(matched, {}) if matched else {}

def _select_training_pair(sources: dict) -> tuple[str, str, dict, dict]:
    """
    Stage 0 메타데이터의 role/id_columns를 기준으로 telemetry와 failure 파일을 짝짓는다.
    파일명 키워드나 family_id 문자열 완전 일치는 더 이상 사용하지 않는다.
    """
    registry = load_family_registry()

    telemetry_candidates = [
        k for k in sources if _get_file_meta(k, registry).get("role") == "telemetry_sensor"
    ]
    failure_candidates = [
        k for k in sources if _get_file_meta(k, registry).get("role") in ("failure_event", "evaluation_truth")
    ]

    if not telemetry_candidates:
        raise ValueError("role='telemetry_sensor'로 판별된 파일이 없습니다. Stage 0 메타데이터를 확인해주세요.")
    if not failure_candidates:
        raise ValueError("role='failure_event'로 판별된 파일이 없습니다. Stage 0 메타데이터를 확인해주세요.")

    for t_key in telemetry_candidates:
        t_meta = _get_file_meta(t_key, registry)
        t_ids = set(t_meta.get("id_columns", []))
        for f_key in failure_candidates:
            f_meta = _get_file_meta(f_key, registry)
            f_ids = set(f_meta.get("id_columns", []))
            if t_ids & f_ids:
                logger.info(
                    f"[TrainAll] Stage 0 메타데이터 기준 매칭 성공: telemetry='{t_key}'(role={t_meta.get('role')}), "
                    f"failure='{f_key}'(role={f_meta.get('role')}), 공통 id_columns={t_ids & f_ids}"
                )
                return t_key, f_key, t_meta, f_meta

    raise ValueError(
        "telemetry_sensor와 failure_event 역할을 가진 파일들 중 id_columns가 겹치는 "
        "조합을 찾지 못했습니다. Stage 0 메타데이터(source_family_registry.json)를 확인해주세요."
    )

def train_all(data_dir: str = "data", store_dir: str = "models_store", force_reanalyze: bool = False):
    logger.info("========================================")
    logger.info(f"🚀 RUNNING TRAINING PIPELINE (v3): Data Directory = '{data_dir}', force_reanalyze = {force_reanalyze}")
    logger.info("========================================")
    
    logger.info(">>> STEP 1: PARSE & EXTRACT SOURCES (Extraction Agent)")
    sources = load_all_sources(data_dir, force_reanalyze=force_reanalyze)

    # --- 부가 산출물(raw_extracted/) 저장은 메인 학습 파이프라인과 완벽히 격리 ---
    try:
        from systems.generator.extraction.raw_extracted_writer import persist_raw_extracted
        from systems.generator.extraction.loader import get_last_plans
        persist_raw_extracted(sources, get_last_plans(), force_reanalyze)
    except Exception as e:
        logger.warning(f"[TrainAll] raw_extracted 저장 단계 전체 실패(학습은 계속 진행): {e}")
    # --- 부가 산출물 저장 끝 ---

    logger.info(">>> STEP 2: ONTOLOGY MAPPING")
    store = get_mapping_store()
    map_all_sources(sources, store)
    reload_mapping_store()
    
    logger.info(">>> STEP 3: CAPABILITY DETECTION")
    capabilities = detect_capabilities(store)

    logger.info(">>> STEP 4: STAGE 0 METADATA PAIR SELECTION & FEATURE EXTRACTION")
    telemetry_key, failures_key, telemetry_meta, failure_meta = _select_training_pair(sources)
    family_id = telemetry_meta.get("family_id", "unknown")
    id_col = telemetry_meta.get("id_col") or "asset_id"
    time_col = telemetry_meta.get("time_col") or "observed_at"

    catalog = load_catalog()
    features = build_features(sources[telemetry_key], store, catalog)
    save_features_npy(features, "data_preprocessed/features", telemetry_key)

    logger.info(">>> STEP 5: LABELING (with Stage 0 time_columns semantics)")
    labeled = build_labels(features, sources[failures_key], failure_meta=failure_meta)
    train_positive_rate = float(labeled["label"].mean())
    logger.info(f"Training dataset positive rate for telemetry='{telemetry_key}' & failure='{failures_key}': {train_positive_rate:.4f}")

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
        "source_failures_key": failures_key,
        "id_col": id_col,
        "time_col": time_col,
        "telemetry_role": telemetry_meta.get("role"),
        "failure_role": failure_meta.get("role"),
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
