import sys
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Root 경로 sys.path 추가
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# systems/ 내부 도메인 서비스 직접 import
from systems.generator.model.train_all_models import train_all
from systems.backend.app.diagnosis.diagnosis_service import predict_all
from systems.backend.app.report.generator import generate_report

app = FastAPI(title="Manufacturing Ontology Platform API (systems/ architecture)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrainRequest(BaseModel):
    data_dir: str = "data"
    force_reanalyze: bool = False

@app.post("/api/train")
def api_train(req: TrainRequest):
    logger.info(f"[API] Training request received. Target data_dir: {req.data_dir}")
    data_path = os.path.join(ROOT_DIR, req.data_dir)
    if not os.path.exists(data_path) or not os.listdir(data_path):
        raise HTTPException(status_code=400, detail=f"'{data_path}' 데이터 디렉터리가 존재하지 않거나 비어 있습니다.")
    try:
        result = train_all(data_dir=data_path, force_reanalyze=req.force_reanalyze)
        return result
    except Exception as e:
        logger.exception("Error during training pipeline")
        raise HTTPException(status_code=500, detail=str(e))

class PredictRequest(BaseModel):
    rows: list[dict]

@app.post("/api/predict")
def api_predict(req: PredictRequest):
    logger.info(f"[API] Predict request received for {len(req.rows)} rows.")
    try:
        predictions = predict_all(req.rows)
        return {"predictions": predictions}
    except Exception as e:
        logger.exception("Error during prediction pipeline")
        raise HTTPException(status_code=500, detail=str(e))

class ReportRequest(BaseModel):
    report_type: str = "predictive_inspection_request"
    params: dict = {}

@app.post("/api/report")
def api_report(req: ReportRequest):
    logger.info(f"[API] Report request received for type: {req.report_type}")
    try:
        report_output = generate_report(req.report_type, **req.params)
        return report_output
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Error during report generation")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sample-telemetry")
def api_sample_telemetry(n: int = 20):
    import pandas as pd
    data_path = os.path.join(ROOT_DIR, "data", "PdM_telemetry.csv")
    if not os.path.exists(data_path):
        data_path = os.path.join(ROOT_DIR, "data", "compressor_sensor_observation.csv")
    try:
        df = pd.read_csv(data_path)
        sample = df.tail(n)
        return {"rows": sample.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"샘플 데이터 로드 실패: {e}")


def _format_size_label(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _inspect_file(rel_path: str, full_path: str) -> dict:
    size_bytes = os.path.getsize(full_path)
    size_label = _format_size_label(size_bytes)
    oversized = size_bytes >= 100 * 1024 * 1024  # 100MB 이상 경고
    ext = os.path.splitext(full_path)[1].lower()

    preview = None
    note = None

    binary_exts = {".npy", ".joblib", ".pkl", ".bin", ".pyc"}
    if ext in binary_exts:
        note = "바이너리 파일 — 미리보기 불가"
    elif ext == ".csv":
        try:
            lines = []
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(4):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
            preview = "".join(lines)
        except Exception as e:
            note = f"미리보기 실패: {e}"
    elif ext == ".json":
        if size_bytes <= 1024 * 1024:  # 1MB 이하만 전체 미리보기
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    preview = f.read()
            except Exception as e:
                note = f"미리보기 실패: {e}"
        else:
            note = "1MB 초과 JSON 파일 — 미리보기 생략"
    else:
        # 일반 텍스트 파일 4줄 미리보기
        try:
            lines = []
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(4):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
            preview = "".join(lines) if lines else None
        except Exception:
            note = "미리보기 불가"

    return {
        "name": os.path.basename(full_path),
        "path": rel_path.replace("\\", "/"),
        "size_bytes": size_bytes,
        "size_label": size_label,
        "type": ext.lstrip("."),
        "preview": preview,
        "note": note,
        "oversized_warning": oversized
    }


def _scan_directory_files(rel_dir: str, recursive: bool = False) -> list[dict]:
    abs_dir = os.path.join(ROOT_DIR, rel_dir)
    if not os.path.exists(abs_dir):
        return []

    files_list = []
    if recursive:
        for root, _, files in os.walk(abs_dir):
            for file in sorted(files):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ROOT_DIR)
                files_list.append(_inspect_file(rel_path, full_path))
    else:
        for item in sorted(os.listdir(abs_dir)):
            full_path = os.path.join(abs_dir, item)
            if os.path.isfile(full_path):
                rel_path = os.path.relpath(full_path, ROOT_DIR)
                files_list.append(_inspect_file(rel_path, full_path))

    return files_list


@app.get("/api/files/lineage")
def get_files_lineage():
    from datetime import datetime, timezone
    
    raw_files = _scan_directory_files("data", recursive=False)

    step1_files = _scan_directory_files(os.path.join("data_preprocessed", "raw_extracted"), recursive=True)
    step2_files = _scan_directory_files(os.path.join("data_preprocessed", "features"), recursive=True)
    step3_files = _scan_directory_files("models_store", recursive=True)

    return {
        "raw": {
            "group_label": "data/",
            "files": raw_files
        },
        "processed": {
            "groups": [
                {
                    "group_label": "1단계 · data_preprocessed/raw_extracted/",
                    "files": step1_files
                },
                {
                    "group_label": "2단계 · data_preprocessed/features/",
                    "files": step2_files
                },
                {
                    "group_label": "3단계 · models_store/",
                    "files": step3_files
                }
            ]
        },
        "scanned_at": datetime.now(timezone.utc).isoformat()
    }

