import os
import sys
import logging
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)

_config_loaded = False

def load_config():
    global _config_loaded
    if not _config_loaded:
        env_file = find_dotenv(usecwd=True)
        if env_file:
            load_dotenv(env_file)
        else:
            cur = os.path.abspath(__file__)
            for _ in range(6):
                cur = os.path.dirname(cur)
                target = os.path.join(cur, ".env")
                if os.path.exists(target):
                    load_dotenv(target)
                    break
        _config_loaded = True

def call_llm(prompt: str, system: str = "You are a helpful assistant.") -> str:
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
    load_config()  # 단독 실행이므로 .env 로딩을 여기서 직접 보장

    test_system = "You are a helpful assistant."
    test_prompt = "다음 문장을 한 문장으로 요약해줘: 오늘 날씨는 맑고 기온은 섭씨 22도입니다."

    print("=" * 60)
    print("[openai_client.py 단독 실행 -- LLM 연결 테스트]")
    print("=" * 60)
    print(f"\n[INPUT - system]\n{test_system}")
    print(f"\n[INPUT - prompt]\n{test_prompt}")

    try:
        result = call_llm(test_prompt, system=test_system)
        print(f"\n[OUTPUT]\n{result}")
        print("\n[SUCCESS] LLM 호출 성공 -- API 키와 .env 로딩이 정상 작동합니다.")
    except Exception as e:
        print(f"\n[FAIL] LLM 호출 실패: {e}")
        print("   .env의 OPENAI_API_KEY 설정을 확인해주세요.")
