from systems.generator.model.lightgbm import LightGBMModel
from systems.generator.model.xgboost import XGBoostModel
from systems.generator.model.random_forest import RandomForestModel

REGISTERED_MODELS = {
    "lightgbm": LightGBMModel,
    "xgboost": XGBoostModel,
    "random_forest": RandomForestModel,
}
