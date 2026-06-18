"""Sales analytics routes computed from orders and product data."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from bson import ObjectId
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _build_date_filter(start_date: Optional[str], end_date: Optional[str]) -> dict:
    """Build a Mongo filter on createdAt from optional ISO date strings."""
    if not (start_date or end_date):
        return {}
    created = {}
    if start_date:
        try:
            created["$gte"] = datetime.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            # A date-only endDate parses to midnight; extend to end of day so
            # same-day orders created later are still included.
            if len(end_date) == 10:
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            created["$lte"] = end_dt
        except ValueError:
            pass
    return {"createdAt": created} if created else {}


def _revenue_by_period(orders: list) -> list:
    """Group order revenue by day (YYYY-MM-DD), sorted ascending."""
    period_map = {}
    for order in orders:
        created = order.get("createdAt")
        if not created:
            continue
        if isinstance(created, datetime):
            period = created.strftime("%Y-%m-%d")
        else:
            period = str(created)[:10]
        period_map[period] = round(period_map.get(period, 0) + order.get("total", 0), 2)
    return [{"period": k, "revenue": v} for k, v in sorted(period_map.items())]


async def _top_products(orders: list) -> list:
    """Aggregate the top 10 products by quantity sold, enriched with names."""
    product_stats = {}
    for order in orders:
        for item in order.get("items", []):
            pid = item.get("productId")
            if not pid:
                continue
            # Normalize to str so productId stored as ObjectId and as string group together.
            pid = str(pid)
            product_stats[pid] = product_stats.get(pid, 0) + item.get("quantity", 0)

    ranked = sorted(product_stats.items(), key=lambda kv: kv[1], reverse=True)[:10]

    top = []
    for pid, quantity in ranked:
        name = pid
        price = 0
        try:
            product = await products_collection.find_one({"_id": ObjectId(pid)})
            if product:
                name = product.get("name", pid)
                price = product.get("price", 0) or 0
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        revenue = round(price * quantity, 2)
        top.append({
            "productId": pid,
            "id": pid,
            "name": name,
            "productName": name,
            "quantity": quantity,
            "totalQuantity": quantity,
            "revenue": revenue,
            "totalRevenue": revenue,
        })
    return top


@router.get("/sales")
async def get_sales_analytics(
    start_date: Optional[str] = Query(None, alias="startDate"),
    end_date: Optional[str] = Query(None, alias="endDate"),
    _current_user: dict = Depends(get_current_user),
):
    """Return total revenue, order count, top products and revenue by period."""
    date_filter = _build_date_filter(start_date, end_date)
    orders = await orders_collection.find(date_filter).to_list(length=None)

    if not orders:
        return {
            "totalRevenue": 0,
            "totalOrders": 0,
            "topProducts": [],
            "revenueByPeriod": [],
        }

    return {
        "totalRevenue": round(sum(o.get("total", 0) for o in orders), 2),
        "totalOrders": len(orders),
        "topProducts": await _top_products(orders),
        "revenueByPeriod": _revenue_by_period(orders),
    }
