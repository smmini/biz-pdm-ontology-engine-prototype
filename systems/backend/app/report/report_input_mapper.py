import os
import json
import logging
from datetime import datetime, timezone
from systems.generator.infrastructure.llm.openai_client import call_llm
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

def _load_env_safely():
    env_file = find_dotenv(usecwd=True)
    if env_file:
        load_dotenv(env_file)

REPORT_INPUT_MAPPING_PATH = "data_preprocessed/report_input_mapping.json"

# 두 마크다운 문서의 ReportOutput이 요구하는 입력 필드(요약)
REPORT_REQUIRED_INPUT_FIELDS = {
    "predictive_inspection_request": [
        "model_prediction.status_grade", "model_prediction.probability",
        "model_prediction.confidence", "model_prediction.model_version",
        "top_factors[].feature", "top_factors[].raw_contribution", "top_factors[].direction",
        "asset_id", "observed_at",
    ],
    "predictive_maintenance_status_summary": [
        "assets[].asset_id", "assets[].status_grade", "assets[].probability",
        "assets[].display_name", "assets[].location_label",
    ],
}

# 실제 파이프라인이 만들어내는 데이터 필드(PredictionOutput 스키마 기준)
AVAILABLE_INTERNAL_FIELDS = [
    "failure_probability", "confidence", "status_grade", "predicted_failure_type",
    "prediction_timestamp", "feature_importance", "shap_values",
]

def build_report_input_mapping(force_reanalyze: bool = False) -> dict:
    """
    Stage A: 실제 내부 데이터 필드(PredictionOutput 등)를 두 마크다운 문서의
    ReportOutput 입력 요구사항과 LLM으로 대조해서, 어느 내부 필드가 어느 리포트
    입력 필드에 대응하는지 매핑 파일을 만든다. 이미 파일이 있으면 재생성하지 않는다
    (한 번만 판단하고 이후엔 정적으로 재사용).
    """
    _load_env_safely()
    if os.path.exists(REPORT_INPUT_MAPPING_PATH) and not force_reanalyze:
        logger.info(f"[ReportInputMapper] 캐시 존재, 재생성 생략: '{REPORT_INPUT_MAPPING_PATH}'")
        with open(REPORT_INPUT_MAPPING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    system_prompt = (
        "당신은 예지보전 시스템의 데이터 필드 매핑 전문가입니다.\n"
        "내부 파이프라인이 실제로 생성하는 필드 목록과, 리포트 출력이 요구하는 "
        "입력 필드 목록을 비교해서, 어느 내부 필드가 어느 리포트 입력 필드에 "
        "대응하는지 매핑하세요. 대응이 불명확한 필드는 target을 null로 두세요.\n"
        "JSON으로만 응답: {\"mappings\": [{\"internal_field\": \"...\", "
        "\"report_field\": \"...\" | null, \"confidence\": 0.0~1.0}]}"
    )
    user_prompt = (
        f"내부 필드: {AVAILABLE_INTERNAL_FIELDS}\n"
        f"리포트 요구 필드: {REPORT_REQUIRED_INPUT_FIELDS}"
    )

    try:
        raw = call_llm(user_prompt, system=system_prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0]
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        mapping = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mappings": parsed.get("mappings", []),
        }
    except Exception as e:
        logger.warning(f"[ReportInputMapper] LLM 매핑 실패, 기본 매핑으로 대체: {e}")
        mapping = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mappings": [
                {"internal_field": "status_grade", "report_field": "model_prediction.status_grade", "confidence": 0.6},
                {"internal_field": "failure_probability", "report_field": "model_prediction.probability", "confidence": 0.6},
                {"internal_field": "confidence", "report_field": "model_prediction.confidence", "confidence": 0.6},
                {"internal_field": "prediction_timestamp", "report_field": "observed_at", "confidence": 0.6},
            ],
        }

    os.makedirs(os.path.dirname(REPORT_INPUT_MAPPING_PATH), exist_ok=True)
    with open(REPORT_INPUT_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    logger.info(f"[ReportInputMapper] 매핑 파일 생성 완료: '{REPORT_INPUT_MAPPING_PATH}'")
    return mapping
