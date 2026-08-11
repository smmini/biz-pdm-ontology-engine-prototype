import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

RAW_EXTRACTED_DIR = "data_preprocessed/raw_extracted"

def persist_raw_extracted(sources: dict, plans: dict, force_reanalyze: bool) -> None:
    """
    학습 파이프라인과 완전히 분리된 참고용 저장 단계.
    이 함수 전체가 실패해도(어떤 파일 하나가 문제든, 디렉터리 접근 문제든)
    호출부는 예외를 전파받지 않는다 - 내부에서 전부 처리하고 로그만 남긴다.
    """
    try:
        os.makedirs(RAW_EXTRACTED_DIR, exist_ok=True)
    except Exception as e:
        logger.warning(f"[RawExtractedWriter] 디렉터리 생성 실패, 저장 단계 전체를 건너뜁니다: {e}")
        return

    for key, df in sources.items():
        try:
            plan = plans.get(key, {})
            out_name = os.path.splitext(plan.get("filename", f"{key}.csv"))[0] + ".csv"
            out_path = os.path.join(RAW_EXTRACTED_DIR, out_name)

            if os.path.exists(out_path) and not force_reanalyze:
                logger.info(f"[RawExtractedWriter] 캐시 존재, 재저장 생략: '{out_path}'")
                continue

            df.to_csv(out_path, index=False)
            logger.info(f"[RawExtractedWriter] 저장 완료: '{out_path}' ({len(df)} rows)")
        except Exception as e:
            # 파일 하나가 실패해도 나머지 파일 저장은 계속 진행한다.
            logger.warning(f"[RawExtractedWriter] '{key}' 저장 실패(건너뛰고 계속 진행): {e}")
            continue
