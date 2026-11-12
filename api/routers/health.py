from fastapi import APIRouter

from api.models import HealthResponse, MetaResponse, ModelItem, ModelsResponse
from api.store import store
from src.common.constants import BASELINE_MODEL, MODELS
from src.common.paths import is_mock

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    if not store.is_loaded:
        store.load()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        mock=is_mock(),
        artifacts_loaded=store.is_loaded,
    )


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    return MetaResponse(**store.meta)


@router.get("/models", response_model=ModelsResponse)
def get_models() -> ModelsResponse:
    meta_models = store.meta.get("models", MODELS)
    model_labels = {
        "ensemble": "Ensemble",
        "lgbm": "LightGBM",
        "xgboost": "XGBoost",
        "prophet": "Prophet",
        "lstm": "LSTM",
        "linear": "Linear Regression",
        "seasonal_naive": "Seasonal naive (same hour last week)",
    }
    model_kinds = {
        "ensemble": "ensemble",
        "seasonal_naive": "baseline",
        "linear": "baseline",
        "lgbm": "tree",
        "xgboost": "tree",
        "prophet": "additive",
        "lstm": "deep",
    }
    items = []
    for m in meta_models:
        items.append(
            ModelItem(
                id=m,
                label=model_labels.get(m, m),
                kind=model_kinds.get(m, "ml"),
                is_baseline=(m == BASELINE_MODEL or m == "linear"),
            )
        )
    return ModelsResponse(models=items)
