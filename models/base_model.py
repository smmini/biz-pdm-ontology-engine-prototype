from abc import ABC, abstractmethod
import pandas as pd
from prediction.output_schema import PredictionOutput

class BasePredictionModel(ABC):
    """
    모든 Prediction 모델이 상속받아야 하는 공통 인터페이스입니다.
    """

    @abstractmethod
    def train(self, df: pd.DataFrame, target_col: str):
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame) -> PredictionOutput:
        """
        예측 결과는 반드시 PredictionOutput 스키마를 따라야 합니다.
        """
        pass

    @abstractmethod
    def save(self, path: str):
        pass

    @abstractmethod
    def load(self, path: str):
        pass
