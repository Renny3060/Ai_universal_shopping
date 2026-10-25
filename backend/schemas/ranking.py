from typing import Optional

from pydantic import BaseModel, Field

from backend.schemas.product import ProductResult


class RankedProduct(BaseModel):
    product: ProductResult
    shipping: Optional[float] = None      # None = desconhecido
    taxes: float = 0.0
    total_cost: float
    category: Optional[str] = None
    score: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class RejectedProduct(BaseModel):
    product: ProductResult
    reason: str