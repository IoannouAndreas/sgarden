from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user
from datetime import datetime

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sales")
async def get_sales_analytics(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    date_filter = {}
    if startDate or endDate:
        date_filter["createdAt"] = {}
        if startDate:
            date_filter["createdAt"]["$gte"] = datetime.fromisoformat(startDate)
        if endDate:
            date_filter["createdAt"]["$lte"] = datetime.fromisoformat(endDate)

    pipeline = [
        {"$match": date_filter},
        {
            "$facet": {
                "summary": [
                    {
                        "$group": {
                            "_id": None,
                            "totalRevenue": {"$sum": "$total"},
                            "totalOrders": {"$sum": 1},
                        }
                    }
                ],
                "topProducts": [
                    {"$unwind": "$items"},
                    {
                        "$group": {
                            "_id": "$items.productId",
                            "totalQuantity": {"$sum": "$items.quantity"},
                            "totalRevenue": {"$sum": {"$multiply": ["$items.quantity", "$total"]}},
                        }
                    },
                    {"$sort": {"totalQuantity": -1}},
                    {"$limit": 10},
                ],
                "revenueByPeriod": [
                    {
                        "$group": {
                            "_id": {
                                "$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}
                            },
                            "revenue": {"$sum": "$total"},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],
            }
        },
    ]

    result = await orders_collection.aggregate(pipeline).to_list(length=1)

    if not result:
        return {"totalRevenue": 0, "totalOrders": 0, "topProducts": [], "revenueByPeriod": []}

    data = result[0]
    summary = data["summary"][0] if data["summary"] else {"totalRevenue": 0, "totalOrders": 0}

    top_products = []
    for item in data["topProducts"]:
        from bson import ObjectId
        try:
            product = await products_collection.find_one({"_id": ObjectId(item["_id"])})
            name = product.get("name") if product else item["_id"]
        except Exception:
            name = item["_id"]
        top_products.append({
            "productId": item["_id"],
            "name": name,
            "totalQuantity": item["totalQuantity"],
            "totalRevenue": round(item["totalRevenue"], 2),
        })

    revenue_by_period = [
        {"period": r["_id"], "revenue": round(r["revenue"], 2)}
        for r in data["revenueByPeriod"]
    ]

    return {
        "totalRevenue": round(summary.get("totalRevenue", 0), 2),
        "totalOrders": summary.get("totalOrders", 0),
        "topProducts": top_products,
        "revenueByPeriod": revenue_by_period,
    }
