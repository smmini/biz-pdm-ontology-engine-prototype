from abc import ABC, abstractmethod
import pandas as pd
from systems.backend.app.diagnosis.diagnosis_schema import PredictionOutput

class BasePredictionModel(ABC):
    """
    모든 Prediction 모델이 상속받아야 하는 공통 인터페이스입니다.
    """

    @abstractmethod
    def train(self, df: pd.DataFrame, target_col: str = "label", id_col: str = None, time_col: str = None):
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame) -> PredictionOutput:
        pass

    @abstractmethod
    def save(self, path: str):
        pass

    @abstractmethod
    def load(self, path: str):
        pass
