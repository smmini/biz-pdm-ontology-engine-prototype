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
