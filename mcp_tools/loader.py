import os
import logging
from mcp_tools.extraction_planner import build_extraction_plan
from mcp_tools.extractor import extract_with_plan

logger = logging.getLogger(__name__)

def load_all_sources(data_dir: str, force_reanalyze: bool = False, save_dir: str = "data_preprocessed/raw_extracted") -> dict:
    os.makedirs(save_dir, exist_ok=True)
    sources = {}
    logger.info(f"[Loader] Scanning directory '{data_dir}' for data files (force_reanalyze={force_reanalyze})...")
    
    for fname in os.listdir(data_dir):
        if not fname.lower().endswith((".csv", ".xlsx", ".xls")):
            continue
        file_path = os.path.join(data_dir, fname)
        key = os.path.splitext(fname)[0]

        logger.info(f"[Loader] Processing file: {fname}")
        plan = build_extraction_plan(file_path, force_reanalyze=force_reanalyze)
        df = extract_with_plan(file_path, plan)

        # 추출된 파싱 결과물 CSV로 디스크 보존
        save_path = os.path.join(save_dir, f"{key}.csv")
        df.to_csv(save_path, index=False)
        logger.info(f"[Loader] Saved extracted dataframe to: {save_path} (shape: {df.shape})")
        
        sources[key] = df

    return sources
