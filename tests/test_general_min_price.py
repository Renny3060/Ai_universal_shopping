from backend.agents.group3_logic.vertical_rules import split_non_vehicles, MIN_PRICE
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct

CFG = {
    "olx": {"verticals": ["tech", "general", "cars", "moto"]},
    "bertrand": {"verticals": ["general"]},
}


def _item(store, price, title="Lego Ninjago"):
    p = ProductResult(store=store, external_id="x", title=title, url="https://x.pt/1", price=price)
    return RankedProduct(product=p, shipping=None, taxes=0.0, total_cost=price, category=None, score=0.0, warnings=[])


def test_general_tem_minimo_de_2_euros():
    assert MIN_PRICE["general"] == 2.0


def test_general_rejeita_cromos_baratos_em_lojas_mistas():
    keep, out = split_non_vehicles([_item("olx", 0.20), _item("olx", 5.0)], "lego ninjago", "general", CFG)
    assert [i.product.price for i in keep] == [5.0]
    assert len(out) == 1 and "mínimo" in out[0].reason


def test_general_nao_filtra_lojas_so_gerais():
    keep, out = split_non_vehicles([_item("bertrand", 1.5)], "lego ninjago", "general", CFG)
    assert len(keep) == 1 and not out


def test_general_nao_corta_por_pecas():
    keep, out = split_non_vehicles([_item("olx", 30.0, "Lego peças soltas")], "lego", "general", CFG)
    assert len(keep) == 1


def test_min_preco_manual_tem_prioridade():
    keep, out = split_non_vehicles([_item("olx", 3.0)], "lego", "general", CFG, min_price=5.0)
    assert not keep and len(out) == 1


def test_tech_continua_sem_filtro():
    keep, out = split_non_vehicles([_item("olx", 0.5)], "rtx", "tech", CFG)
    assert len(keep) == 1 and not out
