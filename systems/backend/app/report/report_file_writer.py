import os
import json
import logging
from datetime import datetime, timezone
from systems.backend.app.report.report_input_mapper import (
    build_report_input_mapping, REPORT_INPUT_MAPPING_PATH,
)
from systems.backend.app.report.report_generator import generate_report

logger = logging.getLogger(__name__)

REPORTS_OUTPUT_DIR = "data_preprocessed/reports"

def _apply_mapping(internal_data: dict, mapping: dict) -> dict:
    """report_input_mapping.json을 참조해서 internal_data를 report_generator의
    kwargs 형태로 변환한다. LLM 호출 없음 — 순수 정적 변환."""
    kwargs = {}
    for m in mapping.get("mappings", []):
        target = m.get("report_field")
        source = m.get("internal_field")
        if not target or source not in internal_data:
            continue
        # "model_prediction.probability" 같은 dot-path를 중첩 dict로 조립
        parts = target.split(".")
        cursor = kwargs
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = internal_data[source]
    return kwargs

def generate_and_save_report(report_type: str, internal_data: dict = None, **extra_kwargs) -> str:
    """
    Stage B: 매핑 파일 기준으로 internal_data를 report_generator에 넘길 kwargs로
    변환하고, 고정 포맷(ReportOutput)을 생성해서 파일로 저장한다.
    반환값: 저장된 파일 경로.
    """
    if internal_data is None:
        internal_data = {}

    mapping = build_report_input_mapping()  # 캐시 있으면 즉시 반환, LLM 재호출 없음
    mapped_kwargs = _apply_mapping(internal_data, mapping)
    
    # extra_kwargs 및 internal_data 직접 탑재 항목 병합 (명시적 값이 매핑보다 우선)
    for k, v in internal_data.items():
        if k not in mapped_kwargs:
            mapped_kwargs[k] = v
    mapped_kwargs.update(extra_kwargs)

    report_output = generate_report(report_type, **mapped_kwargs)

    out_dir = os.path.join(REPORTS_OUTPUT_DIR, report_type)
    os.makedirs(out_dir, exist_ok=True)
    report_id = report_output.get("report_id") or f"{report_type}_{datetime.now(timezone.utc).isoformat()}"
    safe_id = str(report_id).replace("#", "_").replace(":", "-")
    out_path = os.path.join(out_dir, f"{safe_id}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report_output, f, ensure_ascii=False, indent=2)
    logger.info(f"[ReportFileWriter] 리포트 파일 저장 완료: '{out_path}'")

    return out_path
