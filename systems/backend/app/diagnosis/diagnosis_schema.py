from pydantic import BaseModel
from typing import Dict, Optional, List

class PredictionOutput(BaseModel):
    failure_probability: float
    confidence: float
    status_grade: Optional[str] = None
    predicted_failure_type: Optional[str] = None
    prediction_timestamp: str = ""
    feature_importance: Dict[str, float] = {}
    shap_values: Optional[Dict[str, float]] = None
