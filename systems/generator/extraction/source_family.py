import os
import json
import logging
import pandas as pd

logger = logging.getLogger(__name__)

FAMILY_REGISTRY_PATH = "data_preprocessed/source_family_registry.json"

ID_CANDIDATES = ["asset_id", "machineID", "equipment_id", "device_id"]
TIME_CANDIDATES = ["observed_at", "datetime", "timestamp", "time", "date"]

def infer_key_signature(columns: list[str]) -> tuple[str | None, str | None]:
    """
    컬럼 목록에서 id/time 후보를 찾아 시그니처로 반환한다.
    extraction_planner.enforce_key_columns와 동일한 후보 리스트를 재사용해서
    두 곳의 판단 기준이 어긋나지 않게 한다.
    """
    id_col = next((c for c in ID_CANDIDATES if c in columns), None)
    time_col = next((c for c in TIME_CANDIDATES if c in columns), None)
    return id_col, time_col

def compute_family_id(id_col: str | None, time_col: str | None) -> str:
    return f"{id_col or 'unknown'}::{time_col or 'unknown'}"

def build_family_registry(data_dir: str) -> dict:
    """
    data_dir 내 모든 지원 파일(.csv/.xlsx/.xls)의 헤더만 미리 읽어
    (id_col, time_col) 시그니처로 계열을 나누고, 결과를 파일로 저장한다.
    LLM을 호출하지 않는다 — 순수 컬럼명 대조만으로 판단한다.
    """
    logger.info(f"[SourceFamily] Building family registry for data_dir: '{data_dir}'...")
    if not os.path.exists(data_dir):
        logger.warning(f"[SourceFamily] Directory '{data_dir}' missing. Returning empty registry.")
        return {}

    registry = {}
    valid_exts = (".csv", ".xlsx", ".xls")
    for filename in sorted(os.listdir(data_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_exts:
            continue
        filepath = os.path.join(data_dir, filename)
        try:
            preview = pd.read_csv(filepath, nrows=1) if ext == ".csv" else pd.read_excel(filepath, nrows=1)
            id_col, time_col = infer_key_signature(list(preview.columns))
            family_id = compute_family_id(id_col, time_col)
            registry[filename] = {"family_id": family_id, "id_col": id_col, "time_col": time_col}
            logger.info(f"[SourceFamily] File '{filename}' -> Family: '{family_id}' (id: '{id_col}', time: '{time_col}')")
        except Exception as e:
            logger.warning(f"[SourceFamily] Failed to read header for '{filename}': {e}")

    registry_file_path = os.path.abspath(FAMILY_REGISTRY_PATH)
    os.makedirs(os.path.dirname(registry_file_path), exist_ok=True)
    with open(registry_file_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    logger.info(f"[SourceFamily] Family registry saved to '{FAMILY_REGISTRY_PATH}' with {len(registry)} entries.")
    return registry

def load_family_registry() -> dict:
    if not os.path.exists(FAMILY_REGISTRY_PATH):
        return {}
    with open(FAMILY_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
