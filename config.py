import os
from dotenv import load_dotenv

# .env 파일을 읽어 os.environ에 반영
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

# API KEY가 필요한 경우 강제 체크
# if not OPENAI_API_KEY:
#     raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
