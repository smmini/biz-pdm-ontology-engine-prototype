import os
import logging
from systems.generator.extraction.extraction_planner import build_extraction_plan
from systems.generator.extraction.extractor import extract_with_plan

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")

def load_all_sources(data_dir: str, force_reanalyze: bool = False) -> dict:
    """
    data_dir 내의 .csv, .xlsx, .xls 파일 각각에 대해:
    1. build_extraction_plan(filepath, force_reanalyze)로 계획 수립 (캐시 활용)
    2. extract_with_plan(filepath, plan)으로 실제 추출
    3. 결과를 sources[key]에 저장
    """
    logger.info(f"[Loader] Loading all sources from data_dir: '{data_dir}' (force_reanalyze={force_reanalyze})")
    if not os.path.exists(data_dir):
        raise ValueError(f"Directory missing: {data_dir}")

    sources = {}
    for filename in sorted(os.listdir(data_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            filepath = os.path.join(data_dir, filename)
            key = os.path.splitext(filename)[0]
            logger.info(f"[Loader] Processing source file: '{filename}' (key: '{key}')...")
            
            plan = build_extraction_plan(filepath, force_reanalyze=force_reanalyze)
            df = extract_with_plan(filepath, plan)
            sources[key] = df

    logger.info(f"[Loader] Successfully loaded {len(sources)} source datasets from '{data_dir}'.")
    return sources
