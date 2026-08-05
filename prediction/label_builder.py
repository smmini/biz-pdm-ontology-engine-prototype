import pandas as pd
import logging

logger = logging.getLogger(__name__)

def build_labels(feature_df: pd.DataFrame, failures_df: pd.DataFrame, horizon_hours: int = 24) -> pd.DataFrame:
    logger.info(f"[LabelBuilder] Starting label generation. Input features shape: {feature_df.shape}, Failures count: {len(failures_df)}")
    logger.info(f"[LabelBuilder] Label horizon set to {horizon_hours} hours prior to failure.")
    
    df = feature_df.copy()
    df["label"] = 0
    df["datetime"] = pd.to_datetime(df["datetime"])
    failures_df = failures_df.copy()
    failures_df["datetime"] = pd.to_datetime(failures_df["datetime"])

    labeled_count = 0
    for _, row in failures_df.iterrows():
        window_start = row["datetime"] - pd.Timedelta(hours=horizon_hours)
        mask = (
            (df["machineID"] == row["machineID"])
            & (df["datetime"] >= window_start)
            & (df["datetime"] <= row["datetime"])
        )
        matched = mask.sum()
        df.loc[mask, "label"] = 1
        labeled_count += matched
        logger.debug(f"[LabelBuilder] Marked {matched} rows as failure (label=1) for machine '{row['machineID']}' at {row['datetime']}")

    logger.info(f"[LabelBuilder] Completed labeling. Total rows labeled 1: {labeled_count} out of {len(df)}")
    return df
