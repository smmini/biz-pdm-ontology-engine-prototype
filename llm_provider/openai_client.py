from openai import OpenAI
import sys
import os

# root 디렉토리를 sys.path에 추가하여 config.py 로드 가능하게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import OPENAI_API_KEY, OPENAI_MODEL

# 클라이언트를 지연 생성하거나 에러 방지를 위해 None 처리 가능
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def call_llm(prompt: str, system: str = "") -> str:
    if not client:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 LLM을 호출할 수 없습니다.")
        
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
