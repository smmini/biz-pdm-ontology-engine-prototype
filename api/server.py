import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# 기본적인 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# root 디렉토리를 sys.path에 추가하여 모듈 임포트가 가능하게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.train_all_models import train_all
from prediction.predict_all import predict_all

app = FastAPI(title="Manufacturing Ontology Platform API (v2)")

# Next.js 프론트엔드와 통신하기 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 배포 시 구체적인 도메인으로 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrainRequest(BaseModel):
    data_dir: str = "data"
    force_reanalyze: bool = False

@app.post("/api/train")
def api_train(req: TrainRequest):
    logger.info(f"API Request received for train. Target directory: {req.data_dir}, force_reanalyze: {req.force_reanalyze}")
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), req.data_dir)
    
    if not os.path.exists(data_path) or not os.listdir(data_path):
        logger.error(f"Data directory not found or empty: {data_path}")
        raise HTTPException(status_code=400, detail=f"'{data_path}' 경로에 데이터 파일이 존재하지 않습니다.")
    
    try:
        result = train_all(data_path, force_reanalyze=req.force_reanalyze)
        logger.info("API training execution finished successfully.")
        return result
    except Exception as e:
        logger.exception("Error during training pipeline")
        raise HTTPException(status_code=500, detail=str(e))

class PredictRequest(BaseModel):
    rows: list[dict]

@app.post("/api/predict")
def api_predict(req: PredictRequest):
    logger.info(f"API Request received for predict with {len(req.rows)} rows.")
    try:
        predictions = predict_all(req.rows)
        return {"predictions": predictions}
    except Exception as e:
        logger.exception("Error during prediction pipeline")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sample-telemetry")
def api_sample_telemetry(n: int = 20):
    """대시보드에서 예측 테스트를 위해 과거 데이터를 샘플링하여 반환"""
    import pandas as pd
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    try:
        df = pd.read_csv(os.path.join(data_path, "PdM_telemetry.csv"))
        # 특정 기기의 최신 n건 추출
        machine_id = df['machineID'].iloc[0]
        sample = df[df['machineID'] == machine_id].tail(n)
        return {"rows": sample.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail="샘플 데이터 로드 실패")
