from fastapi import APIRouter, Depends
from database import products_collection
from security.jwt_handler import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

current_threshold = 10


class ThresholdRequest(BaseModel):
    threshold: int


@router.get("")
async def get_alerts(_current_user: dict = Depends(get_current_user)):
    alerts = []
    async for product in products_collection.find({"stock": {"$lt": current_threshold}}):
        stock = product.get("stock", 0)
        if stock == 0 or stock <= current_threshold * 0.25:
            severity = "critical"
        elif stock <= current_threshold * 0.5:
            severity = "warning"
        else:
            severity = "info"
        alerts.append({
            "productId": str(product["_id"]),
            "name": product.get("name"),
            "stock": stock,
            "severity": severity
        })
    return alerts


@router.put("/threshold")
async def set_threshold(request: ThresholdRequest, _current_user: dict = Depends(get_current_user)):
    global current_threshold
    current_threshold = request.threshold
    return {"threshold": current_threshold}
