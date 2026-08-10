import pandas as pd
import numpy as np

def build_labels(features_df: pd.DataFrame, failures_df: pd.DataFrame) -> pd.DataFrame:
    """
    features_df와 failures_df를 머지하여 label(0/1) 컬럼을 생성합니다.
    """
    df = features_df.copy()
    
    # machineID/asset_id 및 datetime/observed_at 통일
    id_col = "asset_id" if "asset_id" in df.columns else ("machineID" if "machineID" in df.columns else None)
    fail_id_col = "asset_id" if "asset_id" in failures_df.columns else ("machineID" if "machineID" in failures_df.columns else None)
    
    time_col = "observed_at" if "observed_at" in df.columns else ("datetime" if "datetime" in df.columns else None)
    fail_time_col = "observed_at" if "observed_at" in failures_df.columns else ("datetime" if "datetime" in failures_df.columns else None)

    if id_col and fail_id_col and time_col and fail_time_col:
        fail_events = set(zip(failures_df[fail_id_col], failures_df[fail_time_col]))
        df["label"] = df.apply(lambda row: 1 if (row[id_col], row[time_col]) in fail_events else 0, axis=1)
    else:
        # 실패 이벤트가 지정되지 않은 경우 0으로 기본 채움
        df["label"] = 0

    return df
