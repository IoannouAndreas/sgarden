"""Low-stock alert routes and configurable stock threshold."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database import products_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# Mutable module-level holder for the alert threshold. Using a dict (rather than a
# bare reassigned variable) keeps the name a constant and avoids the global statement.
THRESHOLD = {"value": 10}


class ThresholdRequest(BaseModel):
    """Payload for updating the low-stock threshold."""
    threshold: int


@router.get("")
async def get_alerts(_current_user: dict = Depends(get_current_user)):
    """Return low-stock alerts with product info and a severity level."""
    threshold = THRESHOLD["value"]
    alerts = []
    async for product in products_collection.find({"stock": {"$lt": threshold}}):
        stock = product.get("stock", 0)
        if stock == 0 or stock <= threshold * 0.25:
            severity = "critical"
        elif stock <= threshold * 0.5:
            severity = "warning"
        else:
            severity = "info"
        alerts.append({
            "productId": str(product["_id"]),
            "name": product.get("name"),
            "productName": product.get("name"),
            "category": product.get("category"),
            "price": product.get("price"),
            "stock": stock,
            "severity": severity,
        })
    return alerts


@router.put("/threshold")
async def set_threshold(request: ThresholdRequest, _current_user: dict = Depends(get_current_user)):
    """Update the low-stock threshold and return the new value."""
    THRESHOLD["value"] = request.threshold
    return {"threshold": THRESHOLD["value"]}
