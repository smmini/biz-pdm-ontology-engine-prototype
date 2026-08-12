import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_config_loaded = False

def load_config(force: bool = False) -> None:
    global _config_loaded
    if _config_loaded and not force:
        return
    # 이 파일(systems/generator/generator_config.py) 기준 3단계 상위 = 레포 루트
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f"[GeneratorConfig] Loaded '{env_path}'")
    else:
        logger.warning(f"[GeneratorConfig] .env not found at '{env_path}'.")
    _config_loaded = True
