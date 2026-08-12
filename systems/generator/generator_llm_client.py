import os
import sys
import logging

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from openai import OpenAI
from systems.generator.generator_config import load_config

logger = logging.getLogger(__name__)

def call_llm(prompt: str, system: str = "You are a helpful assistant.") -> str:
    """
    Generator 전용 LLM 호출 클라이언트.
    GeneratorConfig를 로드한 뒤 OpenAI API를 직접 호출한다.
    """
    load_config()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY environment variable is missing.")
        raise ValueError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Generator LLM Client Standalone Self-Test ===")
    try:
        res = call_llm("Ping! Reply with 'PONG' only.", system="You are a test assistant.")
        print(f"[SUCCESS] Response: '{res}'")
    except Exception as e:
        print(f"[FAIL] Error during LLM call: {e}")
