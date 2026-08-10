"""
Facade adapter for backward compatibility with existing prediction calls.
Forwards predict_all calls to systems.backend.app.diagnosis.diagnosis_service.
"""
from systems.backend.app.diagnosis.diagnosis_service import predict_all

__all__ = ["predict_all"]
