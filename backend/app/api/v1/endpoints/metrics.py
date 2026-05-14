from fastapi import APIRouter

from app.core.metrics import metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics() -> dict:
    return metrics.snapshot()
