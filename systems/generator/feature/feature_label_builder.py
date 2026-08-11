import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def build_labels(features_df: pd.DataFrame, failures_df: pd.DataFrame, failure_meta: dict | None = None) -> pd.DataFrame:
    """
    features_df와 failures_df를 머지하여 label(0/1) 컬럼을 생성합니다.
    Stage 0 파일 메타데이터(failure_meta)가 존재할 시 time_columns의 semantic(period_start, period_end/failure_point)을
    참조하여 고장 구간 매칭(Interval-based Labeling)을 수행합니다.
    """
    df = features_df.copy()

    id_col = "asset_id" if "asset_id" in df.columns else ("machineID" if "machineID" in df.columns else None)
    time_col = "observed_at" if "observed_at" in df.columns else ("datetime" if "datetime" in df.columns else None)

    fail_id_col = "asset_id" if "asset_id" in failures_df.columns else ("machineID" if "machineID" in failures_df.columns else None)

    # Stage 0 메타데이터에서 구간 시작/끝 컬럼 조회
    time_cols_meta = (failure_meta or {}).get("time_columns", [])
    start_col = next((c["name"] for c in time_cols_meta if c.get("semantic") == "period_start"), None)
    end_col = next((c["name"] for c in time_cols_meta if c.get("semantic") in ("failure_point", "period_end", "maintenance_end")), None)

    if id_col and fail_id_col and time_col and start_col and end_col \
            and start_col in failures_df.columns and end_col in failures_df.columns:
        logger.info(f"[LabelBuilder] 구간 매칭 사용: start='{start_col}', end='{end_col}' (id_col='{id_col}')")
        df["label"] = 0
        fdf = failures_df[[fail_id_col, start_col, end_col]].dropna()
        for _, row in fdf.iterrows():
            mask = (
                (df[id_col] == row[fail_id_col]) &
                (df[time_col] >= row[start_col]) &
                (df[time_col] <= row[end_col])
            )
            df.loc[mask, "label"] = 1
        pos_count = (df["label"] == 1).sum()
        logger.info(f"[LabelBuilder] 구간 매칭 완료. 총 {len(df)}행 중 positive label: {pos_count}행 ({pos_count/len(df):.4f})")
        return df

    # 메타데이터에 구간 정보가 없는 경우: 기존 정확 시각 일치 로직
    fail_time_col = "observed_at" if "observed_at" in failures_df.columns else ("datetime" if "datetime" in failures_df.columns else None)
    if id_col and fail_id_col and time_col and fail_time_col:
        logger.info(f"[LabelBuilder] 정확 시각 일치 매칭 사용 (구간 메타데이터 없음): id='{id_col}', time='{time_col}'")
        fail_events = set(zip(failures_df[fail_id_col], failures_df[fail_time_col]))
        df["label"] = df.apply(lambda r: 1 if (r[id_col], r[time_col]) in fail_events else 0, axis=1)
        pos_count = (df["label"] == 1).sum()
        logger.info(f"[LabelBuilder] 정확 시각 일치 매칭 완료. 총 {len(df)}행 중 positive label: {pos_count}행 ({pos_count/len(df):.4f})")
    else:
        logger.warning("[LabelBuilder] id/time 컬럼을 찾지 못해 label을 전부 0으로 채웁니다.")
        df["label"] = 0

    return df
