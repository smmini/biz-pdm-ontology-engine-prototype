import logging
from systems.generator.generator_config import load_config
from systems.generator.infrastructure.llm.openai_client import call_llm as _call_llm

logger = logging.getLogger(__name__)

def call_llm(prompt: str, system: str = "You are a helpful assistant.") -> str:
    """
    Generator 전용 LLM 호출 클라이언트.
    독립된 generator_config를 최우선으로 로드한 후 LLM을 구동한다.
    """
    load_config()
    return _call_llm(prompt, system=system)
