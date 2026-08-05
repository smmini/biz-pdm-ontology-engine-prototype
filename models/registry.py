from models.lightgbm import LightGBMModel
from models.xgboost import XGBoostModel
from models.random_forest import RandomForestModel

REGISTERED_MODELS = {
    "lightgbm": LightGBMModel,
    "xgboost": XGBoostModel,
    "random_forest": RandomForestModel,
}
