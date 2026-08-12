import os
import pytest

def test_systems_root_has_no_python_files():
    """
    systems/ 최상위에는 공용 파이썬 모듈(.py)이 존재하지 않고
    generator/, backend/, frontend/ 3개 컨테이너 디렉터리만 존재해야 한다.
    """
    systems_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "systems"))
    assert os.path.exists(systems_dir), "systems 디렉터리가 존재해야 합니다."
    
    entries = os.listdir(systems_dir)
    py_files = [f for f in entries if f.endswith(".py")]
    
    assert len(py_files) == 0, f"systems/ 최상위에 파이썬 파일이 남아있으면 안 됩니다: {py_files}"
    
    # 3개 디렉터리 존재 검증
    for container in ["generator", "backend", "frontend"]:
        container_path = os.path.join(systems_dir, container)
        assert os.path.isdir(container_path), f"systems/{container} 디렉터리가 존재해야 합니다."

def test_generator_config_isolation():
    """
    Generator 전용 config 모듈이 독립적으로 동작하는지 검증
    """
    from systems.generator.generator_config import load_config as load_gen_config
    load_gen_config(force=True)

def test_backend_config_isolation():
    """
    Backend 전용 config 모듈이 독립적으로 동작하는지 검증
    """
    from systems.backend.backend_config import load_config as load_backend_config
    load_backend_config(force=True)

def test_generator_llm_client_import():
    """
    Generator 전용 LLM 클라이언트 import 무결성 검증
    """
    from systems.generator.generator_llm_client import call_llm
    assert callable(call_llm)
