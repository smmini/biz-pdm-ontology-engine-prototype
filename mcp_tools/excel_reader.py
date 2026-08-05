import pandas as pd

def read_excel(file_path: str) -> pd.DataFrame:
    """
    Excel 파일을 읽어 DataFrame으로 반환합니다.
    """
    return pd.read_excel(file_path)
