"""Pydantic models for products."""
from typing import Optional
from pydantic import BaseModel


class ProductRequest(BaseModel):
    """Payload for creating or updating a product."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
