from fastapi import APIRouter, HTTPException, status, Depends
from models.order import OrderRequest
from database import orders_collection, products_collection
from security.jwt_handler import get_current_user
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/orders", tags=["orders"])


def order_to_response(order: dict) -> dict:
    return {
        "id": str(order["_id"]),
        "items": order.get("items", []),
        "total": order.get("total", 0),
        "createdAt": order.get("createdAt").isoformat() if order.get("createdAt") else None,
        "updatedAt": order.get("updatedAt").isoformat() if order.get("updatedAt") else None,
    }


async def calculate_total(items: list) -> float:
    """Fetch each product's price and multiply by quantity."""
    total = 0.0
    for item in items:
        product = await products_collection.find_one({"_id": ObjectId(item["productId"])})
        if product and product.get("price") is not None:
            total += product["price"] * item["quantity"]
    return round(total, 2)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderRequest, current_user: dict = Depends(get_current_user)):
    items = [{"productId": i.productId, "quantity": i.quantity} for i in request.items]
    total = await calculate_total(items)

    order_doc = {
        "items": items,
        "total": total,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await orders_collection.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id
    return order_to_response(order_doc)


@router.get("")
async def get_all_orders(current_user: dict = Depends(get_current_user)):
    orders = []
    async for order in orders_collection.find():
        orders.append(order_to_response(order))
    return orders


@router.get("/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return order_to_response(order)


@router.put("/{order_id}")
async def update_order(order_id: str, request: OrderRequest, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    items = [{"productId": i.productId, "quantity": i.quantity} for i in request.items]
    total = await calculate_total(items)

    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"items": items, "total": total, "updatedAt": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    return order_to_response(order)


@router.delete("/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {"message": "Order deleted"}