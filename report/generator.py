from prediction.output_schema import PredictionOutput
from ontology.mapping_store import MappingStore
from llm_provider.openai_client import call_llm
import logging

logger = logging.getLogger(__name__)

def generate_report(prediction: PredictionOutput, mappings: MappingStore, env_capabilities: dict) -> str:
    logger.info("[ReportGenerator] Starting report generation...")
    logger.info(f"[ReportGenerator] Inputs - Failure Prob: {prediction.failure_probability:.2f}, Capabilities: {env_capabilities}")
    base = (
        f"### 이상 감지 리포트\n\n"
        f"- 예측 고장 유형: {prediction.failure_type}\n"
        f"- 고장 확률: {prediction.failure_probability * 100:.2f}%\n"
        f"- 예측 신뢰도: {prediction.confidence * 100:.2f}%\n"
    )

    if env_capabilities.get("Maintenance", False):
        base += "\n#### 유지보수 권장사항\n유지보수 이력이 있는 환경이므로, 관련 권장사항을 도출합니다.\n"

    top_features = sorted(prediction.feature_importance.items(), key=lambda x: -x[1])[:3]
    prompt = (
        f"다음 예측 결과를 바탕으로 현장 엔지니어가 이해하기 쉬운 2~3문장 요약을 작성하세요.\n"
        f"고장확률={prediction.failure_probability:.2f}, 신뢰도={prediction.confidence:.2f}, "
        f"주요 기여 요인={top_features}"
    )
    
    logger.debug(f"[ReportGenerator] Prompting LLM: {prompt}")
    try:
        narrative = call_llm(prompt, system="당신은 설비 예지보전 전문가입니다. 간결하고 실무적으로 작성하세요.")
        logger.info(f"[ReportGenerator] Successfully generated LLM narrative (length: {len(narrative)} chars)")
        base += f"\n#### 종합 소견\n{narrative}\n"
    except Exception as e:
        logger.warning(f"[ReportGenerator] LLM Generation failed: {str(e)}")
        base += "\n#### 종합 소견\n(LLM 요약 생략: OPENAI_API_KEY 미설정 또는 오류)\n"

    logger.info("[ReportGenerator] Report generation completed.")
    return base
