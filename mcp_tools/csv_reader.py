import pandas as pd

def read_csv(file_path: str) -> pd.DataFrame:
    """
    CSV 파일을 읽어 DataFrame으로 반환합니다.
    (Agent는 직접 파일을 파싱하지 않고 이 툴을 이용해 데이터에 접근합니다.)
    """
    return pd.read_csv(file_path)
