from fastapi import APIRouter, Depends
from typing import Optional
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sales")
async def get_sales_analytics(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    date_filter = {}
    if startDate or endDate:
        date_filter["createdAt"] = {}
        if startDate:
            try:
                date_filter["createdAt"]["$gte"] = datetime.fromisoformat(startDate)
            except Exception:
                pass
        if endDate:
            try:
                date_filter["createdAt"]["$lte"] = datetime.fromisoformat(endDate)
            except Exception:
                pass

    orders = await orders_collection.find(date_filter).to_list(length=None)

    if not orders:
        return {
            "totalRevenue": 0,
            "totalOrders": 0,
            "topProducts": [],
            "revenueByPeriod": [],
        }

    total_revenue = round(sum(o.get("total", 0) for o in orders), 2)
    total_orders = len(orders)

    # Revenue by period (group by date)
    period_map = {}
    for order in orders:
        created = order.get("createdAt")
        if created:
            period = created.strftime("%Y-%m-%d") if isinstance(created, datetime) else str(created)[:10]
            period_map[period] = round(period_map.get(period, 0) + order.get("total", 0), 2)
    revenue_by_period = [{"period": k, "revenue": v} for k, v in sorted(period_map.items())]

    # Top products — aggregate quantity per productId
    product_stats = {}
    for order in orders:
        for item in order.get("items", []):
            pid = item.get("productId")
            if not pid:
                continue
            if pid not in product_stats:
                product_stats[pid] = {"totalQuantity": 0}
            product_stats[pid]["totalQuantity"] += item.get("quantity", 0)

    sorted_products = sorted(product_stats.items(), key=lambda x: x[1]["totalQuantity"], reverse=True)[:10]

    top_products = []
    for pid, stats in sorted_products:
        try:
            product = await products_collection.find_one({"_id": ObjectId(pid)})
            name = product.get("name") if product else pid
            price = product.get("price", 0) if product else 0
        except Exception:
            name = pid
            price = 0
        top_products.append({
            "productId": pid,
            "name": name,
            "totalQuantity": stats["totalQuantity"],
            "totalRevenue": round(price * stats["totalQuantity"], 2),
        })

    return {
        "totalRevenue": total_revenue,
        "totalOrders": total_orders,
        "topProducts": top_products,
        "revenueByPeriod": revenue_by_period,
    }
