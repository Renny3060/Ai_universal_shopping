from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.db import models  # noqa: F401  (regista as tabelas)
from backend.db.database import Base
from backend.db.models import PriceHistory, Product
from backend.services.favorites import (
    FavoriteError,
    add_favorite,
    list_favorites,
    remove_favorite,
    set_target_price,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")          # base em memória: não toca em shopping.db
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(Product(store="pcdiga", external_id="p1", title="Placa A", url="https://x/a"))
        session.commit()
        yield session


def test_add_cria_favorito_e_pasta(db):
    fav = add_favorite(db, "pcdiga", "p1", folder_name="Build PC", note="boa", target_price=400)
    assert fav.id
    assert fav.folder.name == "Build PC"
    assert fav.target_price == 400


def test_add_repetido_atualiza_sem_duplicar(db):
    a = add_favorite(db, "pcdiga", "p1", note="1")
    b = add_favorite(db, "pcdiga", "p1", note="2")
    items = list_favorites(db)
    assert a.id == b.id
    assert len(items) == 1
    assert items[0].note == "2"


def test_produto_inexistente(db):
    with pytest.raises(FavoriteError):
        add_favorite(db, "pcdiga", "nao-existe")


def test_preco_alvo_invalido(db):
    with pytest.raises(FavoriteError):
        add_favorite(db, "pcdiga", "p1", target_price=0)


def test_ultimo_preco_e_abaixo_do_alvo(db):
    now = datetime.now(timezone.utc)
    prod = db.query(Product).first()
    db.add_all([
        PriceHistory(product_id=prod.id, price=500, total_cost=500, recorded_at=now - timedelta(days=1)),
        PriceHistory(product_id=prod.id, price=450, total_cost=450, recorded_at=now),
    ])
    db.commit()
    add_favorite(db, "pcdiga", "p1", target_price=460)
    item = list_favorites(db)[0]
    assert item.last_price == 450
    assert item.below_target


def test_remover(db):
    fav = add_favorite(db, "pcdiga", "p1")
    assert remove_favorite(db, fav.id) is True
    assert list_favorites(db) == []
    assert remove_favorite(db, fav.id) is False


def test_limpar_preco_alvo(db):
    fav = add_favorite(db, "pcdiga", "p1", target_price=300)
    set_target_price(db, fav.id, None)
    assert list_favorites(db)[0].target_price is None