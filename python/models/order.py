from pydantic import BaseModel
from typing import List

class OrderItem(BaseModel):
    productId: str
    quantity: int

class OrderRequest(BaseModel):
    items: List[OrderItem]