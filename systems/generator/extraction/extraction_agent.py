import os
import json
import logging
import hashlib
import pandas as pd
from systems.generator.infrastructure.llm.openai_client import call_llm

logger = logging.getLogger(__name__)

EXTRACTION_PLAN_CACHE_PATH = "data_preprocessed/extraction_plan_cache.json"

_plan_cache: dict = {}
_cache_mtime: float = 0.0

def load_plan_cache() -> dict:
    global _plan_cache, _cache_mtime
    if os.path.exists(EXTRACTION_PLAN_CACHE_PATH):
        mtime = os.path.getmtime(EXTRACTION_PLAN_CACHE_PATH)
        if _cache_mtime == mtime and _plan_cache:
            return _plan_cache
        try:
            with open(EXTRACTION_PLAN_CACHE_PATH, "r", encoding="utf-8") as f:
                _plan_cache = json.load(f)
                _cache_mtime = mtime
                return _plan_cache
        except Exception as e:
            logger.warning(f"[ExtractionPlanner] Failed to load plan cache: {e}")
    _plan_cache = {}
    return _plan_cache

def save_plan_cache(cache: dict):
    global _plan_cache, _cache_mtime
    os.makedirs(os.path.dirname(os.path.abspath(EXTRACTION_PLAN_CACHE_PATH)), exist_ok=True)
    with open(EXTRACTION_PLAN_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    _plan_cache = cache
    if os.path.exists(EXTRACTION_PLAN_CACHE_PATH):
        _cache_mtime = os.path.getmtime(EXTRACTION_PLAN_CACHE_PATH)

def compute_fingerprint(df_preview: pd.DataFrame) -> str:
    """
    df_preview의 컬럼명과 헤더 샘플 텍스트를 기반으로 md5 해시 생성
    """
    raw_str = f"cols:{list(df_preview.columns)}|head:{df_preview.head(3).to_json()}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()

def classify_structure(filepath: str, df_preview: pd.DataFrame) -> str:
    """
    Stage 1: 오직 파일 구조 타입만 판별한다.
    반환: tabular_column_as_attribute / tabular_row_as_attribute / wide_pivot / unsupported
    """
    system_prompt = (
        "You are a manufacturing data structure classifier.\n"
        "Classify the input table format into EXACTLY ONE of the following structure types:\n"
        "- tabular_column_as_attribute: Standard table where each column is an attribute/sensor feature.\n"
        "- tabular_row_as_attribute: Long format table where rows contain sensor attribute names and values.\n"
        "- wide_pivot: Wide format matrix requiring reshaping.\n"
        "- unsupported: Unparseable unstructured text or binary.\n\n"
        "Respond ONLY with a JSON object: {\"structure_type\": \"...\", \"reason\": \"...\"}"
    )
    prompt = f"File: {os.path.basename(filepath)}\nColumns: {list(df_preview.columns)}\nSample:\n{df_preview.head(3).to_string()}"
    
    try:
        res = call_llm(prompt, system=system_prompt)
        parsed = json.loads(res)
        st_type = parsed.get("structure_type", "tabular_column_as_attribute")
        logger.info(f"[ExtractionPlanner] Stage 1 structure classification for '{filepath}': {st_type}")
        return st_type
    except Exception as e:
        logger.warning(f"[ExtractionPlanner] Stage 1 classification failed: {e}. Defaulting to tabular_column_as_attribute.")
        return "tabular_column_as_attribute"

def plan_extraction(filepath: str, structure_type: str, df_preview: pd.DataFrame) -> list[str]:
    """
    Stage 2: 오직 추출할 컬럼 목록만 선택한다.
    """
    system_prompt = (
        "You are a dataset column selector for manufacturing predictive maintenance.\n"
        "Select all relevant telemetry sensors, time/date fields, and asset identifiers for model analysis.\n"
        "Respond ONLY with a JSON object: {\"selected_columns\": [\"col1\", \"col2\", ...]}"
    )
    prompt = (
        f"File: {os.path.basename(filepath)}\n"
        f"Structure Type: {structure_type}\n"
        f"Available Columns: {list(df_preview.columns)}\n"
        f"Sample:\n{df_preview.head(3).to_string()}"
    )
    
    try:
        res = call_llm(prompt, system=system_prompt)
        parsed = json.loads(res)
        cols = parsed.get("selected_columns", list(df_preview.columns))
        logger.info(f"[ExtractionPlanner] Stage 2 column selection for '{filepath}': {cols}")
        return cols
    except Exception as e:
        logger.warning(f"[ExtractionPlanner] Stage 2 column selection failed: {e}. Fallback to all columns.")
        return list(df_preview.columns)

def enforce_key_columns(selected_columns: list[str], available_columns: list[str]) -> list[str]:
    """
    machineID/asset_id, datetime/observed_at 등의 주요 식별자/시간축 키가 누락되었을 시
    available_columns에서 찾아 강제로 보존한다.
    """
    result = list(selected_columns)
    
    # 식별자 키 후보
    id_candidates = ["asset_id", "machineID", "equipment_id", "device_id", "asset", "machine"]
    time_candidates = ["observed_at", "datetime", "timestamp", "time", "date"]
    
    has_id = any(c in result for c in id_candidates)
    if not has_id:
        found_id = next((c for c in available_columns if c in id_candidates), None)
        if found_id and found_id not in result:
            result.append(found_id)
            logger.info(f"[ExtractionPlanner] Enforced key column ID: '{found_id}'")

    has_time = any(c in result for c in time_candidates)
    if not has_time:
        found_time = next((c for c in available_columns if c in time_candidates), None)
        if found_time and found_time not in result:
            result.append(found_time)
            logger.info(f"[ExtractionPlanner] Enforced key column Time: '{found_time}'")

    return result

def build_extraction_plan(filepath: str, force_reanalyze: bool = False) -> dict:
    """
    오케스트레이션 함수:
    1. compute_fingerprint로 캐시 조회 (force_reanalyze=True면 무조건 재분석)
    2. 캐시 히트 시 즉시 반환 (LLM 미호출)
    3. 캐시 미스 시 Stage 1 classify_structure -> Stage 2 plan_extraction -> enforce_key_columns 순서 실행
    4. 결과를 EXTRACTION_PLAN_CACHE_PATH에 저장 후 반환
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        df_preview = pd.read_csv(filepath, nrows=5)
    elif ext in (".xlsx", ".xls"):
        df_preview = pd.read_excel(filepath, nrows=5)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    fingerprint = compute_fingerprint(df_preview)
    cache = load_plan_cache()
    
    file_key = os.path.basename(filepath)
    if not force_reanalyze and file_key in cache:
        cached_plan = cache[file_key]
        if cached_plan.get("fingerprint") == fingerprint:
            logger.info(f"[ExtractionPlanner] Cache HIT for '{file_key}'. Reusing plan without LLM calls.")
            return cached_plan

    logger.info(f"[ExtractionPlanner] Cache MISS for '{file_key}'. Executing 2-stage LLM plan analysis...")
    structure_type = classify_structure(filepath, df_preview)
    if structure_type == "unsupported":
        raise NotImplementedError(f"File '{filepath}' classified as unsupported format.")

    raw_selected = plan_extraction(filepath, structure_type, df_preview)
    final_selected = enforce_key_columns(raw_selected, list(df_preview.columns))

    plan = {
        "filepath": filepath,
        "filename": file_key,
        "fingerprint": fingerprint,
        "structure_type": structure_type,
        "selected_columns": final_selected
    }

    cache[file_key] = plan
    save_plan_cache(cache)
    logger.info(f"[ExtractionPlanner] Saved new extraction plan for '{file_key}' into cache.")
    return plan
