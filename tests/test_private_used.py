from backend.agents.group2_search.stores import STORES
from backend.agents.group3_logic.financial_agent import apply_costs
from backend.agents.group3_logic.scoring_agent import rank
from backend.schemas.product import ProductResult


def _p(store: str, price: float, cond: str, eid: str = "1") -> ProductResult:
    return ProductResult(store=store, external_id=eid, title="Item", url="https://x.pt/1",
                         price=price, condition=cond)


def test_aviso_particular_so_na_olx():
    items = apply_costs([_p("olx", 10, "used"), _p("pcdiga", 10, "new", "2")], STORES)
    assert any("particular" in w for w in items[0].warnings)
    assert not any("particular" in w for w in items[1].warnings)


def test_usado_penalizado_mais_que_novo():
    items = rank(apply_costs([_p("olx", 100, "used"), _p("pcdiga", 100, "new", "2")], STORES))
    assert items[0].product.condition == "new"
    assert items[0].score - items[1].score >= 12


def test_usado_barato_ainda_pode_ganhar():
    items = rank(apply_costs([_p("olx", 60, "used"), _p("pcdiga", 100, "new", "2")], STORES))
    assert items[0].product.condition == "used"