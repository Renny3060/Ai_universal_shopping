from typing import Optional

from pydantic import BaseModel


class ProductResult(BaseModel):
    """Um artigo encontrado numa loja (saída dos agentes do Grupo 2)."""
    store: str
    external_id: str
    title: str
    url: str
    price: float
    currency: str = "EUR"
    image_url: Optional[str] = None
    shipping: Optional[float] = None
    seller_name: Optional[str] = None
    seller_rating: Optional[float] = None
    origin_country: Optional[str] = None
    condition: str = "new"
    in_stock: bool = True