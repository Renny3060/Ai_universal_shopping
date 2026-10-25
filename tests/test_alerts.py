from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.db import models  # noqa: F401  (regista as tabelas)
from backend.db.database import Base
from backend.db.models import PriceHistory, Product
from backend.services.alerts import check_alerts
from backend.services.favorites import add_favorite

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")          # base em memória: não toca em shopping.db
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(Product(store="pcdiga", external_id="p1", title="Placa A", url="https://x/a"))
        session.commit()
        yield session


def history(db, points):
    """points: lista de (dias_atrás, preço)."""
    prod = db.query(Product).first()
    for days_ago, price in points:
        db.add(PriceHistory(product_id=prod.id, price=price, total_cost=price,
                            recorded_at=NOW - timedelta(days=days_ago)))
    db.commit()


def kinds(db, **kw):
    return [a.kind for a in check_alerts(db, now=NOW, **kw)]


def test_preco_alvo_atingido(db):
    add_favorite(db, "pcdiga", "p1", target_price=460)
    history(db, [(3, 500), (0, 450)])
    assert "target_reached" in kinds(db)


def test_sem_alerta_se_acima_do_alvo_e_estavel(db):
    add_favorite(db, "pcdiga", "p1", target_price=400)
    history(db, [(3, 500), (0, 500)])
    assert kinds(db) == []


def test_descida_de_preco(db):
    add_favorite(db, "pcdiga", "p1")
    history(db, [(3, 500), (0, 450)])
    assert kinds(db) == ["price_drop"]


def test_descida_pequena_nao_alerta(db):
    add_favorite(db, "pcdiga", "p1")
    history(db, [(3, 500), (0, 490)])
    assert kinds(db) == []


def test_promocao_falsa_sobe_e_volta(db):
    add_favorite(db, "pcdiga", "p1")
    history(db, [(20, 400), (10, 480), (0, 400)])
    assert kinds(db) == ["suspicious_promo"]      # não anuncia também a "descida"


def test_variacao_pequena_nao_e_promocao_falsa(db):
    add_favorite(db, "pcdiga", "p1")
    history(db, [(20, 400), (10, 405), (0, 400)])
    assert kinds(db) == []


def test_sem_historico_sem_alertas(db):
    add_favorite(db, "pcdiga", "p1", target_price=400)
    assert kinds(db) == []