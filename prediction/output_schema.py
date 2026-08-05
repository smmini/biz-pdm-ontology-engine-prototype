from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class PredictionOutput(BaseModel):
    failure_probability: float = Field(..., description="고장 확률 (0.0 ~ 1.0)")
    failure_type: str = Field(..., description="예측된 고장 유형")
    confidence: float = Field(..., description="예측 신뢰도")
    prediction_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="예측 시간 (ISO8601)")
    shap: Optional[Dict[str, float]] = Field(default_factory=dict, description="SHAP value를 통한 특성 기여도")
    feature_importance: Optional[Dict[str, float]] = Field(default_factory=dict, description="특성 중요도")
