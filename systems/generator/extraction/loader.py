import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_all_sources(data_dir: str, force_reanalyze: bool = False) -> dict:
    """
    data_dir 내의 CSV 파일들을 읽어 dict로 반환합니다.
    """
    logger.info(f"[Loader] Loading sources from directory: {data_dir}")
    if not os.path.exists(data_dir):
        raise ValueError(f"Directory missing: {data_dir}")

    sources = {}
    for filename in os.listdir(data_dir):
        if filename.endswith(".csv"):
            filepath = os.path.join(data_dir, filename)
            key = os.path.splitext(filename)[0]
            logger.info(f"[Loader] Loading CSV '{filename}' as source key '{key}'...")
            df = pd.read_csv(filepath)
            sources[key] = df

    return sources
