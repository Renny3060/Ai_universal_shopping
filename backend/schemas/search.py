from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Saída do Agente 1: o que o utilizador quer, em parâmetros de pesquisa."""
    product_type: str = Field(description="Tipo de produto, ex.: 'PC gaming', 'auscultadores'")
    keywords: list[str] = Field(description="Palavras-chave para pesquisar nas lojas")
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    condition: Literal["new", "used", "refurbished", "any"] = "any"
    must_have: list[str] = Field(default_factory=list, description="Requisitos obrigatórios")
    nice_to_have: list[str] = Field(default_factory=list, description="Preferências opcionais")
    preferred_brands: list[str] = Field(default_factory=list)


class Requirement(BaseModel):
    attribute: str = Field(description="snake_case, ex.: gpu, ram_gb, storage_gb, cpu_brand")
    operator: Literal[">=", "<=", "==", "contains"]
    value: str
    unit: Optional[str] = None
    mandatory: bool = True


class ProductSpecs(BaseModel):
    """Saída do Agente 2: requisitos técnicos estruturados."""
    category: str
    requirements: list[Requirement] = Field(default_factory=list)


class UserContext(BaseModel):
    """Saída do Agente 4: preferências guardadas na base de dados."""
    country: str
    currency: str
    excluded_stores: list[str] = Field(default_factory=list)


class EnrichedQuery(BaseModel):
    """Resultado final do Grupo 1, entregue ao Grupo 2 (scraping)."""
    raw_text: str
    query: SearchQuery
    specs: ProductSpecs
    derived_constraints: list[Requirement] = Field(default_factory=list)
    user: UserContext