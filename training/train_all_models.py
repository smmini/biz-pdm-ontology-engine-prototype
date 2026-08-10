"""
Facade adapter for backward compatibility with existing training calls.
Forwards train_all calls to systems.generator.model.train_all_models.
"""
from systems.generator.model.train_all_models import train_all

__all__ = ["train_all"]
