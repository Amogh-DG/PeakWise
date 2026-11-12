from fastapi import APIRouter

from api.models import (
    ProcurementDefaultsResponse,
    ProcurementRequest,
    ProcurementResponse,
)
from api.store import store
from src.procurement.advisor import recommend

router = APIRouter(prefix="/procurement", tags=["procurement"])


@router.post("/recommend", response_model=ProcurementResponse)
def post_procurement_recommend(payload: ProcurementRequest) -> ProcurementResponse:
    tariff_dict = payload.tariff.model_dump() if payload.tariff else None
    result = recommend(
        start_date=payload.start_date,
        days=payload.days,
        model=payload.model,
        risk_quantile=payload.risk_quantile,
        tariff=tariff_dict,
    )
    return ProcurementResponse(**result)


@router.get("/defaults", response_model=ProcurementDefaultsResponse)
def get_procurement_defaults() -> ProcurementDefaultsResponse:
    return ProcurementDefaultsResponse(**store.procurement_defaults)
