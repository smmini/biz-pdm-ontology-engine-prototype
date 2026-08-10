import os
from dotenv import load_dotenv

# .env 파일을 읽어 os.environ에 반영
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

# Data directories configuration (canonical v3.1 & gen_data integration)
CANONICAL_V3_1_DIR = os.environ.get("CANONICAL_V3_1_DIR", r"C:\kosa\project\final\predictive_maintenance_canonical_v3.1\canonical\dataset")
GEN_DATA_OUTPUT_DIR = os.environ.get("GEN_DATA_OUTPUT_DIR", r"C:\kosa\project\final\gen_data\output")
PROCESSED_SENSOR_DIR = os.environ.get("PROCESSED_SENSOR_DIR", r"C:\kosa\project\final\ontology_dashboard\data\sensor")
PROCESSED_RESULT_DIR = os.environ.get("PROCESSED_RESULT_DIR", r"C:\kosa\project\final\ontology_dashboard\data\result")

