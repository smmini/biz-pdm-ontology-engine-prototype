import os
import json
import hashlib
import logging
from llm_provider.openai_client import call_llm
from mcp_tools.raw_preview import raw_preview

logger = logging.getLogger(__name__)

CACHE_PATH = "mcp_tools/extraction_plan_cache.json"

STRUCTURE_SYSTEM_PROMPT = """당신은 제조 데이터 파일의 구조를 판별하는 전문가입니다.
아래는 파일의 원본 미리보기(가공되지 않은 상태)입니다.

이 데이터가 다음 중 어떤 구조인지 판단하세요. 이 단계에서는 구조 판별만 하고,
어떤 컬럼을 쓸지는 아직 결정하지 마세요.

- tabular_column_as_attribute : 각 "열"이 하나의 속성, 각 "행"이 하나의 기록
- tabular_row_as_attribute    : 행/열이 뒤집힌 형태. 각 "행"이 하나의 속성
- wide_pivot                  : 날짜/시간 등이 열 이름으로 펼쳐진 형태
- key_value                   : 속성명과 값이 2열로만 구성된 형태
- multi_header                : 헤더가 여러 행에 걸쳐 있거나 병합된 형태
- unsupported                 : 위 어디에도 맞지 않는 구조

반드시 JSON으로만 답하세요:
{"structure_type": "...", "sheet_name": "...", "header_row": 0, "confidence": 0.0, "reason": "..."}
"""

EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """당신은 제조 데이터에서 실제로 사용할 attribute를 선택하는 전문가입니다.
이 파일의 구조는 이미 '{structure_type}'로 판별되었습니다 (판별 이유: {structure_reason}).

이 구조를 전제로, 아래 원본 미리보기에서 제조 도메인과 관련된 attribute만 선택하세요.
내부 관리용 ID, 빈 컬럼, 주석성 컬럼은 제외하세요.

반드시 JSON으로만 답하세요:
{{"selected_columns": ["..."], "excluded_columns": ["..."], "confidence": 0.0, "reason": "..."}}
"""

ALWAYS_INCLUDE = {"machineid", "datetime", "timestamp", "time", "date"}

def classify_structure(preview: dict) -> dict:
    logger.info("[ExtractionPlanner] Calling LLM Stage 1: Classifying structure...")
    raw = call_llm(json.dumps(preview, ensure_ascii=False), system=STRUCTURE_SYSTEM_PROMPT)
    # JSON 파싱 전후 청소
    clean_raw = raw.strip()
    if clean_raw.startswith("```json"):
        clean_raw = clean_raw[7:-3].strip()
    elif clean_raw.startswith("```"):
        clean_raw = clean_raw[3:-3].strip()
    return json.loads(clean_raw)

def plan_extraction(preview: dict, structure_result: dict) -> dict:
    logger.info("[ExtractionPlanner] Calling LLM Stage 2: Planning extraction...")
    system = EXTRACTION_SYSTEM_PROMPT_TEMPLATE.format(
        structure_type=structure_result["structure_type"],
        structure_reason=structure_result["reason"],
    )
    raw = call_llm(json.dumps(preview, ensure_ascii=False), system=system)
    clean_raw = raw.strip()
    if clean_raw.startswith("```json"):
        clean_raw = clean_raw[7:-3].strip()
    elif clean_raw.startswith("```"):
        clean_raw = clean_raw[3:-3].strip()
    return json.loads(clean_raw)

def compute_fingerprint(preview: dict) -> str:
    raw = json.dumps(preview, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

def load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def extract_preview_columns(preview: dict, header_row: int = 0) -> list[str]:
    """미리보기 내용에서 파일의 전체 컬럼(헤더) 목록을 추출"""
    cols = []
    if preview.get("file_type") == "text":
        lines = preview.get("raw_lines", [])
        if len(lines) > header_row:
            line = lines[header_row].strip()
            # 헤더 파싱 (컴마, 탭 등 구분자 처리)
            delimiter = "\t" if "\t" in line else ","
            cols = [c.strip().strip('"') for c in line.split(delimiter)]
    elif preview.get("file_type") == "excel":
        raw_p = preview.get("raw_preview", {})
        for sheet_rows in raw_p.values():
            if len(sheet_rows) > header_row:
                cols = [str(c).strip() for c in sheet_rows[header_row] if c is not None]
                break
    return cols

def enforce_key_columns(plan: dict, preview_columns: list[str]) -> dict:
    """조인/시간축 기준 키 컬럼(machineID, datetime 등)이 LLM에 의해 누락되지 않도록 강제 보존"""
    selected_lower = {c.lower() for c in plan["selected_columns"]}
    for col in preview_columns:
        if col.lower() in ALWAYS_INCLUDE and col.lower() not in selected_lower:
            logger.info(f"[ExtractionPlanner] Safety Triggered: Forcibly including essential key column '{col}'")
            plan["selected_columns"].append(col)
            if "excluded_columns" in plan and col in plan["excluded_columns"]:
                plan["excluded_columns"].remove(col)
    return plan

def build_extraction_plan(file_path: str, force_reanalyze: bool = False) -> dict:
    preview = raw_preview(file_path)
    fingerprint = compute_fingerprint(preview)
    cache = load_cache()

    if not force_reanalyze and fingerprint in cache:
        logger.info(f"[ExtractionPlanner] Using cached plan for fingerprint: {fingerprint}")
        return cache[fingerprint]

    structure_result = classify_structure(preview)
    if structure_result["structure_type"] == "unsupported":
        raise NotImplementedError(f"지원하지 않는 구조입니다: {structure_result['reason']}")

    extraction_result = plan_extraction(preview, structure_result)

    plan = {
        "structure_type": structure_result["structure_type"],
        "sheet_name": structure_result.get("sheet_name"),
        "header_row": structure_result.get("header_row", 0),
        "selected_columns": extraction_result["selected_columns"],
        "excluded_columns": extraction_result.get("excluded_columns", []),
        "confidence": min(structure_result.get("confidence", 1.0), extraction_result.get("confidence", 1.0)),
    }

    # 안전장치: 필수 키 컬럼(machineID, datetime) 보존
    preview_cols = extract_preview_columns(preview, header_row=plan["header_row"])
    plan = enforce_key_columns(plan, preview_cols)

    cache[fingerprint] = plan
    save_cache(cache)
    return plan
