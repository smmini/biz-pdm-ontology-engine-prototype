import yaml
import pandas as pd
import numpy as np
import json
import os
import logging
from ontology.mapping_store import MappingStore

logger = logging.getLogger(__name__)

def load_catalog(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "catalog.yaml")
    logger.info(f"[FeatureBuilder] Loading feature catalog from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        catalog = yaml.safe_load(f)["features"]
        logger.info(f"[FeatureBuilder] Loaded catalog rules for nodes: {list(catalog.keys())}")
        return catalog

def build_features(telemetry_df: pd.DataFrame, store: MappingStore, catalog: dict) -> pd.DataFrame:
    """
    telemetry_df의 각 컬럼을 Ontology Node로 치환한 뒤,
    catalog에 정의된 규칙(rolling_mean 등)을 적용해 Feature를 생성한다.
    """
    logger.info(f"[FeatureBuilder] Starting feature extraction on dataset shape: {telemetry_df.shape}")
    df = telemetry_df.copy()
    result = df[["datetime", "machineID"]].copy()

    for col in df.columns:
        mapping = store.get_mapping(col)
        if not mapping or mapping.target_ontology not in catalog:
            continue
        node = mapping.target_ontology
        logger.info(f"[FeatureBuilder] Applying features for column '{col}' mapped to '{node}'...")
        
        for rule in catalog[node]:
            name = rule["name"]
            feat_name = f"{node}_{name}"
            if name == "rolling_mean":
                result[feat_name] = df[col].rolling(rule.get("window", 5)).mean()
            elif name == "rolling_std":
                result[feat_name] = df[col].rolling(rule.get("window", 5)).std()
            elif name == "gradient":
                result[feat_name] = df[col].diff()
            elif name == "ema":
                result[feat_name] = df[col].ewm(span=rule.get("span", 10)).mean()
            elif name == "lag":
                result[feat_name] = df[col].shift(rule.get("periods", 1))
            elif name == "moving_average":
                result[feat_name] = df[col].rolling(rule.get("window", 10)).mean()
            
            logger.debug(f"[FeatureBuilder] Generated feature '{feat_name}'")

    final_df = result.dropna()
    logger.info(f"[FeatureBuilder] Completed feature extraction. Output shape (after dropna): {final_df.shape}")
    return final_df

def save_features_npy(features_df: pd.DataFrame, out_dir: str, name: str):
    os.makedirs(out_dir, exist_ok=True)
    feature_cols = [c for c in features_df.columns if c not in ("datetime", "machineID")]

    np.save(os.path.join(out_dir, f"{name}_X.npy"), features_df[feature_cols].to_numpy())
    np.save(os.path.join(out_dir, f"{name}_machineID.npy"), features_df["machineID"].to_numpy())
    np.save(os.path.join(out_dir, f"{name}_datetime.npy"), features_df["datetime"].to_numpy(dtype="datetime64[ns]"))

    with open(os.path.join(out_dir, f"{name}_columns.json"), "w", encoding="utf-8") as f:
        json.dump(feature_cols, f, ensure_ascii=False, indent=2)
    logger.info(f"[FeatureBuilder] Saved NPY features to: {out_dir}/{name}_*.npy")

def load_features_npy(out_dir: str, name: str) -> pd.DataFrame:
    X = np.load(os.path.join(out_dir, f"{name}_X.npy"))
    machine_id = np.load(os.path.join(out_dir, f"{name}_machineID.npy"))
    dt = np.load(os.path.join(out_dir, f"{name}_datetime.npy"))
    with open(os.path.join(out_dir, f"{name}_columns.json"), "r", encoding="utf-8") as f:
        columns = json.load(f)

    df = pd.DataFrame(X, columns=columns)
    df["machineID"] = machine_id
    df["datetime"] = dt
    return df
