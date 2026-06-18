"""Pydantic request models for the orders API."""
from typing import List
from pydantic import BaseModel


class OrderItem(BaseModel):
    """A single line item in an order."""
    productId: str
    quantity: int


class OrderRequest(BaseModel):
    """Payload for creating or updating an order."""
    items: List[OrderItem]
