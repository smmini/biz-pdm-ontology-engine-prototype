import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def extract_with_plan(filepath: str, plan: dict) -> pd.DataFrame:
    """
    build_extraction_plan()이 반환한 plan(structure_type + selected_columns)에 따라
    실제 pandas 데이터프레임 로드 및 형태 변환을 수행한다.
    """
    ext = os.path.splitext(filepath)[1].lower()
    logger.info(f"[Extractor] Reading file '{filepath}' (ext: {ext})...")
    
    if ext == ".csv":
        df = pd.read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    structure_type = plan.get("structure_type", "tabular_column_as_attribute")
    selected_cols = plan.get("selected_columns", list(df.columns))

    if structure_type == "tabular_column_as_attribute":
        # actual df에 존재하는 컬럼만 걸러내어 선택
        valid_cols = [c for c in selected_cols if c in df.columns]
        if not valid_cols:
            logger.warning(f"[Extractor] None of the selected columns {selected_cols} exist in '{filepath}'. Keeping all columns.")
            valid_cols = list(df.columns)
        
        extracted_df = df[valid_cols].copy()
        logger.info(f"[Extractor] Successfully extracted {len(valid_cols)} columns from '{filepath}'. Output shape: {extracted_df.shape}")
        return extracted_df

    elif structure_type == "tabular_row_as_attribute":
        # 행 방향 속성을 피벗하는 형태 처리
        logger.info(f"[Extractor] Performing tabular_row_as_attribute transform for '{filepath}'...")
        if len(df.columns) >= 3:
            id_col, attr_col, val_col = df.columns[0], df.columns[1], df.columns[2]
            pivoted = df.pivot(index=id_col, columns=attr_col, values=val_col).reset_index()
            return pivoted
        return df

    elif structure_type == "wide_pivot":
        logger.info(f"[Extractor] Performing wide_pivot transform for '{filepath}'...")
        return df

    else:
        raise NotImplementedError(f"Extraction for structure type '{structure_type}' is not implemented.")
