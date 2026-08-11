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

    logger.info(">>> STEP 4: FEATURE EXTRACTION & NPY SAVE")
    catalog = load_catalog()
    telemetry_key = next((k for k in sources if any(sub in k.lower() for sub in ("telemetry", "sensor", "observation"))), list(sources.keys())[0])
    features = build_features(sources[telemetry_key], store, catalog)
    save_features_npy(features, "data_preprocessed/features", telemetry_key)

    logger.info(">>> STEP 5: LABELING")
    failures_key = next((k for k in sources if "failure" in k.lower()), None)
    if not failures_key:
        raise ValueError("Failure data not found. Cannot train models without failure labels.")
    
    labeled = build_labels(features, sources[failures_key])
    train_positive_rate = float(labeled["label"].mean())
    logger.info(f"Training dataset positive rate: {train_positive_rate:.4f}")

    logger.info(">>> STEP 6: TRAIN & SAVE MODELS")
    results = {}
    for name, cls in REGISTERED_MODELS.items():
        logger.info(f"Training model: {name}")
        model = cls()
        model.train(labeled, target_col="label")

        os.makedirs(os.path.join(store_dir, name), exist_ok=True)
        model_path = os.path.join(store_dir, name, "model.joblib")
        model.save(model_path)
        logger.info(f"Saved {name} to {model_path}")

        results[name] = {
            "path": model_path,
            "train_positive_rate": train_positive_rate,
        }

    logger.info(">>> STEP 7: SAVE REGISTRY METADATA")
    feature_cols = [c for c in labeled.columns if c not in ("datetime", "machineID", "label")]
    registry_meta = {
        "trained_at": datetime.utcnow().isoformat(),
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
