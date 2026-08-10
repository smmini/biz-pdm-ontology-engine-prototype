import yaml
import pandas as pd
import numpy as np
import json
import os
import logging
from systems.generator.ontology_mapping.mapping_store import MappingStore

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
    logger.info(f"[FeatureBuilder] Starting feature extraction on dataset shape: {telemetry_df.shape}")
    df = telemetry_df.copy()
    
    time_col = "observed_at" if "observed_at" in df.columns else ("datetime" if "datetime" in df.columns else df.columns[0])
    id_col = "asset_id" if "asset_id" in df.columns else ("machineID" if "machineID" in df.columns else None)
    
    meta_cols = [time_col]
    if id_col and id_col in df.columns:
        meta_cols.append(id_col)

    result = df[meta_cols].copy()

    for col in df.columns:
        if col in meta_cols:
            continue
        mapping = store.get_mapping(col)
        if not mapping:
            logger.warning(f"[FeatureBuilder] Column '{col}' has no ontology mapping. Skipping feature extraction.")
            continue
        if mapping.target_ontology not in catalog:
            logger.warning(f"[FeatureBuilder] Column '{col}' mapped to '{mapping.target_ontology}', but node is not in catalog.yaml. Skipping.")
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
    meta_cols = {"datetime", "observed_at", "machineID", "asset_id"}
    feature_cols = [c for c in features_df.columns if c not in meta_cols]

    np.save(os.path.join(out_dir, f"{name}_X.npy"), features_df[feature_cols].to_numpy())
    
    id_col = "asset_id" if "asset_id" in features_df.columns else ("machineID" if "machineID" in features_df.columns else None)
    if id_col:
        np.save(os.path.join(out_dir, f"{name}_machineID.npy"), features_df[id_col].to_numpy())
        
    time_col = "observed_at" if "observed_at" in features_df.columns else ("datetime" if "datetime" in features_df.columns else None)
    if time_col:
        np.save(os.path.join(out_dir, f"{name}_datetime.npy"), features_df[time_col].to_numpy(dtype="datetime64[ns]"))

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
