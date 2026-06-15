from pydantic import BaseModel
from typing import List, Optional

class OrderItem(BaseModel):
    productId: str
    quantity: int

class OrderRequest(BaseModel):
    items: List[OrderItem]