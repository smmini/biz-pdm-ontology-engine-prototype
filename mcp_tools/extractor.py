import pandas as pd
import logging

logger = logging.getLogger(__name__)

def extract_with_plan(file_path: str, plan: dict) -> pd.DataFrame:
    structure = plan["structure_type"]
    header_row = plan.get("header_row", 0)
    selected_cols = plan.get("selected_columns", [])

    logger.info(f"[Extractor] Extracting data using structure='{structure}', selected_cols={selected_cols}")

    if structure == "tabular_column_as_attribute":
        if file_path.endswith(".csv") or file_path.endswith(".txt") or file_path.endswith(".tsv"):
            df = pd.read_csv(file_path, header=header_row)
        else:
            sheet_name = plan.get("sheet_name") or 0
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
        
        # 선택된 컬럼 중 실제로 존재하며 중복되지 않은 컬럼만 추출
        existing_cols = [c for c in selected_cols if c in df.columns]
        if not existing_cols:
            logger.warning("[Extractor] None of the selected columns were found in dataframe. Returning full dataframe.")
            return df
        return df[existing_cols]

    elif structure == "tabular_row_as_attribute":
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, header=header_row)
        else:
            sheet_name = plan.get("sheet_name") or 0
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
        return df.set_index(df.columns[0]).T.reset_index()

    elif structure == "wide_pivot":
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, header=header_row)
        else:
            sheet_name = plan.get("sheet_name") or 0
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
        id_col = selected_cols[0] if selected_cols else df.columns[0]
        return df.melt(id_vars=[id_col], var_name="datetime", value_name="value")

    else:
        raise NotImplementedError(f"구조 '{structure}'는 자동 추출을 지원하지 않습니다.")
