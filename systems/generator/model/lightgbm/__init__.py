import lightgbm as lgb
import pandas as pd
import shap
import logging
import joblib
from systems.generator.model.base_model import BasePredictionModel
from systems.backend.app.diagnosis.output_schema import PredictionOutput

logger = logging.getLogger(__name__)

class LightGBMModel(BasePredictionModel):
    name = "lightgbm"
    def __init__(self):
        self.model = None
        self.feature_cols = None

    def train(self, df: pd.DataFrame, target_col: str = "label"):
        self.feature_cols = [c for c in df.columns if c not in ("datetime", "observed_at", "machineID", "asset_id", target_col)]
        logger.info(f"[LightGBM] Starting training. Target: '{target_col}', Feature count: {len(self.feature_cols)}")
        
        X, y = df[self.feature_cols], df[target_col]
        self.model = lgb.LGBMClassifier()
        self.model.fit(X, y)
        logger.info(f"[LightGBM] Training completed.")

    def predict(self, df: pd.DataFrame) -> PredictionOutput:
        logger.info(f"[LightGBM] Starting prediction on shape: {df.shape}")
        
        last_row = df[self.feature_cols].iloc[[-1]]
        proba = self.model.predict_proba(last_row)[0][1]

        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(last_row)
        
        import numpy as np
        if isinstance(shap_values, list):
            sv = np.array(shap_values[1])[0]
        elif isinstance(shap_values, np.ndarray):
            if len(shap_values.shape) == 3:
                sv = shap_values[0, :, 1]
            else:
                sv = shap_values[0]
        else:
            sv = np.array(shap_values)[0]
            
        sv = np.array(sv).flatten()
        shap_dict = dict(zip(self.feature_cols, [float(v) for v in sv]))
        importance = dict(zip(self.feature_cols, [float(v) for v in self.model.feature_importances_]))

        return PredictionOutput(
            failure_probability=float(proba),
            confidence=float(max(proba, 1 - proba)),
            feature_importance=importance,
            shap_values=shap_dict
        )

    def save(self, path: str):
        joblib.dump({"model": self.model, "feature_cols": self.feature_cols}, path)

    def load(self, path: str):
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_cols = data["feature_cols"]
