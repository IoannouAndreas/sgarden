from fastapi import APIRouter, HTTPException, status, Depends
from models.product import ProductRequest, ProductResponse
from database import products_collection
from security.jwt_handler import get_current_user
from bson import ObjectId
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/products", tags=["products"])
VALID_CATEGORIES = {"Electronics", "Accessories", "Storage", "Networking"}
service_name = "ProductService"

def validate_product_input(request: ProductRequest, is_create: bool = False) -> dict:
    errors = {}

    # name is required on creation
    if is_create and (not request.name or not request.name.strip()):
        errors["name"] = "Name is required and cannot be empty"

    # price must be positive if provided
    if request.price is not None and request.price <= 0:
        errors["price"] = "Price must be a positive number"

    # category must be one of the valid values if provided
    if request.category is not None and request.category not in VALID_CATEGORIES:
        errors["category"] = f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"

    return errors

def product_to_response(product: dict) -> dict:
    """Convert MongoDB document to API response format."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


def format_product(product: dict) -> dict:
    """CODE QUALITY ISSUE: duplicate of product_to_response above."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


@router.get("/search")
async def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    minPrice: Optional[float] = None,
    maxPrice: Optional[float] = None,
):
    query = {}

    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    if category:
        query["category"] = category

    if minPrice is not None or maxPrice is not None:
        query["price"] = {}
        if minPrice is not None:
            query["price"]["$gte"] = minPrice
        if maxPrice is not None:
            query["price"]["$lte"] = maxPrice

    products = []
    async for product in products_collection.find(query):
        products.append(product_to_response(product))

    return products  # Returns [] automatically if nothing matches


@router.get("/stats")
async def get_product_stats():
    pipeline = [
        {
            "$facet": {
                "summary": [
                    {
                        "$group": {
                            "_id": None,           
                            "totalCount": {"$sum": 1},
                            "averagePrice": {"$avg": "$price"},
                            "minPrice": {"$min": "$price"},
                            "maxPrice": {"$max": "$price"},
                        }
                    }
                ],
                "byCategory": [
                    {"$group": {"_id": "$category", "count": {"$sum": 1}}}
                ],
            }
        }
    ]

    result = await products_collection.aggregate(pipeline).to_list(length=1)

    if not result:
        return {"totalCount": 0, "averagePrice": 0, "minPrice": 0, "maxPrice": 0, "categoryCount": {}}

    data = result[0]
    summary = data["summary"][0] if data["summary"] else {}

    category_count = {
        (item["_id"] if item["_id"] is not None else "Uncategorized"): item["count"]
        for item in data["byCategory"]
    }

    return {
        "totalCount": summary.get("totalCount", 0),
        "averagePrice": round(summary.get("averagePrice", 0), 2),
        "minPrice": summary.get("minPrice", 0),
        "maxPrice": summary.get("maxPrice", 0),
        "categoryCount": category_count,
    }

@router.get("")
async def get_all_products(
    page: Optional[int] = 1,
    limit: Optional[int] = 10,
    sort: Optional[str] = None,
    order: Optional[str] = "asc",
):
    # How many products to skip (e.g. page 2 with limit 5 → skip 5)
    skip = (page - 1) * limit

    # MongoDB sort direction: 1 = ascending, -1 = descending
    sort_direction = 1 if order == "asc" else -1

    # Count total products for the metadata
    total = await products_collection.count_documents({})

    # Build the query: sort if requested, then paginate
    cursor = products_collection.find()
    if sort:
        cursor = cursor.sort(sort, sort_direction)
    cursor = cursor.skip(skip).limit(limit)

    products = []
    async for product in cursor:
        products.append(product_to_response(product))

    # Return structured response with metadata
    return {
        "data": products,   # products for this page
        "page": page,       # current page
        "limit": limit,     # page size
        "total": total,     # total across ALL pages
    }


@router.get("/{product_id}")
async def get_product_by_id(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product_to_response(product)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(request: ProductRequest, current_user: dict = Depends(get_current_user)):
    errors = validate_product_input(request, is_create=True)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": errors}
        )
    
    product_doc = {
        "name": request.name,
        "description": request.description,
        "category": request.category,
        "price": request.price,
        "stock": request.stock if request.stock is not None else 0,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await products_collection.insert_one(product_doc)
    product_doc["_id"] = result.inserted_id
    print(f"Created product: {request.name}")
    return product_to_response(product_doc)


async def update_product_legacy(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    """CODE QUALITY ISSUE: duplicate of update_product."""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.put("/{product_id}")
async def update_product(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    errors = validate_product_input(request, is_create=True)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Validation failed", "errors": errors}
        )
    
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return {"message": "Product deleted"}
