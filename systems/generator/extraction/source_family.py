import os
import json
import logging
from datetime import datetime, timezone
import pandas as pd
from systems.generator.infrastructure.llm.openai_client import call_llm

logger = logging.getLogger(__name__)

FAMILY_REGISTRY_PATH = "data_preprocessed/source_family_registry.json"

ID_CANDIDATES = ["asset_id", "machineID", "equipment_id", "device_id", "asset", "machine"]
TIME_CANDIDATES = ["observed_at", "datetime", "timestamp", "time", "date", "degradation_started_at", "failure_occurred_at", "maintenance_started_at", "maintenance_completed_at"]

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

def profile_source_file_with_llm(filepath: str, filename: str, df_preview: pd.DataFrame) -> dict:
    """
    Stage 0: LLM을 통해 파일의 역할(role), 설명(description), 주요 id/time 컬럼의 의미(semantic),
    전체 컬럼 비고(column_notes)를 프로파일링하여 추적 가능한 메타데이터를 구성한다.
    """
    all_columns = [str(c) for c in df_preview.columns]
    sample_json = df_preview.head(10).to_json(orient="records", date_format="iso")
    
    system_prompt = (
        "You are an expert industrial manufacturing data profiler.\n"
        "Analyze the source dataset file and output a detailed metadata JSON schema.\n"
        "Output ONLY a valid JSON object matching the exact format:\n"
        "{\n"
        '  "role": "failure_event" | "telemetry_sensor" | "maintenance_history" | "machine_master" | "error_event" | "evaluation_truth" | "unknown",\n'
        '  "description": "Clear explanation of what this dataset records and its business context.",\n'
        '  "id_columns": ["asset_id", ...],\n'
        '  "time_columns": [\n'
        '    {"name": "column_name", "semantic": "period_start" | "period_end" | "failure_point" | "maintenance_start" | "timestamp"}\n'
        '  ],\n'
        '  "column_notes": {\n'
        '    "column_name": "note explaining role, unit, or ontology candidate status"\n'
        '  },\n'
        '  "confidence": 0.0 ~ 1.0\n'
        "}"
    )

    user_prompt = f"Filename: {filename}\nColumns ({len(all_columns)}): {all_columns}\nSample Data (up to 10 rows):\n{sample_json}"

    try:
        raw_res = call_llm(user_prompt, system=system_prompt)
        # JSON 블록 파싱
        cleaned = raw_res.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0]
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        
        confidence = float(parsed.get("confidence", 0.90))
        status = "auto_confirmed" if confidence >= 0.7 else "pending"
        
        # id_col, time_col 기본 산출
        id_col, time_col = infer_key_signature(all_columns)
        family_id = compute_family_id(id_col, time_col)
        
        # all_columns 원본 전체 유지 및 column_notes 누락 채움
        col_notes = parsed.get("column_notes", {})
        for col in all_columns:
            if col not in col_notes:
                col_notes[col] = "일반 속성 컬럼"

        time_cols_parsed = parsed.get("time_columns", [])
        if not time_cols_parsed and time_col:
            time_cols_parsed = [{"name": time_col, "semantic": "timestamp"}]

        id_cols_parsed = parsed.get("id_columns", [])
        if not id_cols_parsed and id_col:
            id_cols_parsed = [id_col]

        meta = {
            "family_id": family_id,
            "id_col": id_col,
            "time_col": time_col,
            "role": parsed.get("role", "unknown"),
            "description": parsed.get("description", f"Data source for {filename}"),
            "all_columns": all_columns,
            "id_columns": id_cols_parsed,
            "time_columns": time_cols_parsed,
            "column_notes": col_notes,
            "confidence": confidence,
            "status": status,
            "profiled_at": datetime.now(timezone.utc).isoformat(),
            "provenance": {"model": "gpt-4o-mini", "sample_rows_used": min(10, len(df_preview))}
        }
        return meta
    except Exception as e:
        logger.warning(f"[SourceFamily] LLM profiling failed for '{filename}': {e}. Falling back to rule-based profiling.")
        id_col, time_col = infer_key_signature(all_columns)
        family_id = compute_family_id(id_col, time_col)
        
        role = "failure_event" if "failure" in filename.lower() else ("telemetry_sensor" if any(k in filename.lower() for k in ("telemetry", "sensor", "observation")) else "unknown")
        
        time_cols_rule = []
        for c in all_columns:
            if c in TIME_CANDIDATES:
                semantic = "period_start" if "start" in c else ("period_end" if "end" or "complete" in c else ("failure_point" if "occurred" in c or "fail" in c else "timestamp"))
                time_cols_rule.append({"name": c, "semantic": semantic})

        col_notes_rule = {c: f"컬럼 속성 (자동 할당)" for c in all_columns}
        
        return {
            "family_id": family_id,
            "id_col": id_col,
            "time_col": time_col,
            "role": role,
            "description": f"Rule-based profiled dataset for {filename}",
            "all_columns": all_columns,
            "id_columns": [c for c in all_columns if c in ID_CANDIDATES],
            "time_columns": time_cols_rule if time_cols_rule else ([{"name": time_col, "semantic": "timestamp"}] if time_col else []),
            "column_notes": col_notes_rule,
            "confidence": 0.85,
            "status": "auto_confirmed",
            "profiled_at": datetime.now(timezone.utc).isoformat(),
            "provenance": {"model": "rule_based_fallback", "sample_rows_used": len(df_preview)}
        }

def build_family_registry(data_dir: str, force_reprofile: bool = False) -> dict:
    """
    Stage 0 파이프라인:
    data_dir 내 모든 지원 파일(.csv/.xlsx/.xls)의 전체 컬럼과 구조를 스캔하여
    Stage 0 프로파일링 메타데이터를 구축하고 data_preprocessed/source_family_registry.json에 저장한다.
    이미 프로파일링된 메타데이터가 존재하고 force_reprofile=False이면 파일 캐시를 유지한다.
    """
    logger.info(f"[SourceFamily] Building Stage 0 family registry for data_dir: '{data_dir}' (force_reprofile={force_reprofile})...")
    if not os.path.exists(data_dir):
        logger.warning(f"[SourceFamily] Directory '{data_dir}' missing. Returning empty registry.")
        return {}

    existing_registry = load_family_registry()
    registry = dict(existing_registry)
    valid_exts = (".csv", ".xlsx", ".xls")
    
    updated_count = 0
    for filename in sorted(os.listdir(data_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_exts:
            continue
        
        # 캐시 히트 체크: 이미 프로파일링 필드가 존재하고 force_reprofile이 False이면 유지
        existing_meta = registry.get(filename)
        if not force_reprofile and existing_meta and "role" in existing_meta and "all_columns" in existing_meta:
            logger.info(f"[SourceFamily] Cache Hit for '{filename}' -> keeping Stage 0 metadata.")
            continue

        filepath = os.path.join(data_dir, filename)
        try:
            preview = pd.read_csv(filepath, nrows=10) if ext == ".csv" else pd.read_excel(filepath, nrows=10)
            meta = profile_source_file_with_llm(filepath, filename, preview)
            registry[filename] = meta
            updated_count += 1
            logger.info(f"[SourceFamily] Stage 0 Profiled '{filename}': role='{meta.get('role')}', cols={len(meta.get('all_columns', []))}, confidence={meta.get('confidence')}")
        except Exception as e:
            logger.warning(f"[SourceFamily] Failed to profile '{filename}': {e}")

    registry_file_path = os.path.abspath(FAMILY_REGISTRY_PATH)
    os.makedirs(os.path.dirname(registry_file_path), exist_ok=True)
    with open(registry_file_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    logger.info(f"[SourceFamily] Stage 0 Family registry saved to '{FAMILY_REGISTRY_PATH}' with {len(registry)} entries ({updated_count} profiled).")
    return registry

def load_family_registry() -> dict:
    if not os.path.exists(FAMILY_REGISTRY_PATH):
        return {}
    with open(FAMILY_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

