from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="Utilizador")
    country: Mapped[str] = mapped_column(String(2), default="PT")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    excluded_stores: Mapped[list] = mapped_column(JSON, default=list)
    notification_prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Product(Base):
    """Produto único por loja (ex.: ASIN na Amazon, item ID no eBay)."""
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store", "external_id", name="uq_product_store_extid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    seller_name: Mapped[Optional[str]] = mapped_column(String(200))
    seller_rating: Mapped[Optional[float]] = mapped_column(Float)
    origin_country: Mapped[Optional[str]] = mapped_column(String(2))
    condition: Mapped[str] = mapped_column(String(20), default="new")
    warranty_months: Mapped[Optional[int]] = mapped_column(Integer)
    eu_support: Mapped[Optional[bool]] = mapped_column(default=None)
    specs: Mapped[dict] = mapped_column(JSON, default=dict)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan",
        order_by="PriceHistory.recorded_at",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_product_date", "product_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    price: Mapped[float] = mapped_column(Float)
    shipping: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_known: Mapped[Optional[bool]] = mapped_column(default=None)  # None = registo antigo
    taxes: Mapped[float] = mapped_column(Float, default=0.0)   # IVA / IOSS / alfândega
    total_cost: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    delivery_days: Mapped[Optional[int]] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(default=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped["Product"] = relationship(back_populates="price_history")


class FavoriteFolder(Base):
    __tablename__ = "favorite_folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="folder", cascade="all, delete-orphan"
    )


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("folder_id", "product_id", name="uq_fav_folder_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id: Mapped[int] = mapped_column(ForeignKey("favorite_folders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    note: Mapped[Optional[str]] = mapped_column(Text)
    target_price: Mapped[Optional[float]] = mapped_column(Float)  # para alertas (Agente 17)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    folder: Mapped["FavoriteFolder"] = relationship(back_populates="favorites")
    product: Mapped["Product"] = relationship(back_populates="favorites")


class SearchCache(Base):
    """Pilar 5: cache de resultados para evitar bloqueios de IP."""
    __tablename__ = "search_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # hash da pesquisa
    store: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)