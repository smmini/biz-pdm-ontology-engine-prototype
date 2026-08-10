from pydantic import BaseModel
from typing import Dict, Optional, List

class PredictionOutput(BaseModel):
    failure_probability: float
    confidence: float
    status_grade: Optional[str] = None
    predicted_failure_type: Optional[str] = None
    feature_importance: Dict[str, float] = {}
    shap_values: Optional[List[float]] = None
