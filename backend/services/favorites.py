from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Favorite, FavoriteFolder, PriceHistory, Product


class FavoriteError(Exception):
    """Erro de regras (produto inexistente, preço-alvo inválido, etc.)."""


class FavoriteItem(BaseModel):
    id: int
    folder: str
    store: str
    external_id: str
    title: str
    url: str
    image_url: Optional[str] = None
    note: Optional[str] = None
    target_price: Optional[float] = None
    last_price: Optional[float] = None     # último preço registado no histórico
    below_target: bool = False             # último preço <= preço-alvo


def list_folders(db: Session) -> list[FavoriteFolder]:
    return list(db.scalars(select(FavoriteFolder).order_by(FavoriteFolder.name)))


def create_folder(db: Session, name: str) -> FavoriteFolder:
    """Cria a pasta, ou devolve a existente se o nome já existir."""
    name = name.strip()
    if not name:
        raise FavoriteError("O nome da pasta não pode estar vazio.")
    folder = db.scalars(select(FavoriteFolder).where(FavoriteFolder.name == name)).first()
    if folder is None:
        folder = FavoriteFolder(name=name)
        db.add(folder)
        db.commit()
    return folder


def add_favorite(
    db: Session,
    store: str,
    external_id: str,
    folder_name: str = "Geral",
    note: Optional[str] = None,
    target_price: Optional[float] = None,
) -> Favorite:
    """Guarda um produto numa pasta. Se já lá estiver, só atualiza a nota e o preço-alvo
    que forem indicados. O produto tem de existir na BD (é guardado ao pesquisar)."""
    if target_price is not None and target_price <= 0:
        raise FavoriteError("O preço-alvo tem de ser maior que zero.")

    product = db.scalars(
        select(Product).where(Product.store == store, Product.external_id == external_id)
    ).first()
    if product is None:
        raise FavoriteError("Produto não encontrado na base de dados. Pesquisa-o primeiro.")

    folder = create_folder(db, folder_name)
    fav = db.scalars(
        select(Favorite).where(Favorite.folder_id == folder.id, Favorite.product_id == product.id)
    ).first()

    if fav is None:
        fav = Favorite(folder_id=folder.id, product_id=product.id,
                       note=note, target_price=target_price)
        db.add(fav)
    else:
        if note is not None:
            fav.note = note
        if target_price is not None:
            fav.target_price = target_price
    db.commit()
    return fav


def set_target_price(db: Session, favorite_id: int, target_price: Optional[float]) -> Favorite:
    """Define o preço-alvo de um favorito. None limpa o alvo."""
    if target_price is not None and target_price <= 0:
        raise FavoriteError("O preço-alvo tem de ser maior que zero.")
    fav = db.get(Favorite, favorite_id)
    if fav is None:
        raise FavoriteError("Favorito não encontrado.")
    fav.target_price = target_price
    db.commit()
    return fav


def remove_favorite(db: Session, favorite_id: int) -> bool:
    fav = db.get(Favorite, favorite_id)
    if fav is None:
        return False
    db.delete(fav)
    db.commit()
    return True


def list_favorites(db: Session, folder_name: Optional[str] = None) -> list[FavoriteItem]:
    stmt = select(Favorite).join(FavoriteFolder).order_by(
        FavoriteFolder.name, Favorite.created_at.desc()
    )
    if folder_name:
        stmt = stmt.where(FavoriteFolder.name == folder_name)

    items: list[FavoriteItem] = []
    for fav in db.scalars(stmt):
        prod = fav.product
        last = db.scalars(
            select(PriceHistory)
            .where(PriceHistory.product_id == prod.id)
            .order_by(PriceHistory.recorded_at.desc())
        ).first()
        last_price = last.price if last else None
        below = (
            last_price is not None
            and fav.target_price is not None
            and last_price <= fav.target_price
        )
        items.append(FavoriteItem(
            id=fav.id, folder=fav.folder.name, store=prod.store,
            external_id=prod.external_id, title=prod.title, url=prod.url,
            image_url=prod.image_url, note=fav.note, target_price=fav.target_price,
            last_price=last_price, below_target=below,
        ))
    return items