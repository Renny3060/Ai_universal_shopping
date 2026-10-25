from backend.agents.group3_logic.outliers import split_outliers
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def _item(price: float, n: int) -> RankedProduct:
    p = ProductResult(store="x", external_id=str(n), title=f"RTX 5060 {n}",
                      url=f"https://x.pt/{n}", price=price)
    return RankedProduct(product=p, shipping=None, taxes=0.0, total_cost=price, warnings=[])


def test_rejeita_preco_muito_abaixo_da_mediana():
    items = [_item(p, i) for i, p in enumerate([300, 330, 380, 400, 450, 460, 480, 510, 520, 20.75])]
    ok, rej = split_outliers(items)
    assert len(ok) == 9 and len(rej) == 1
    assert rej[0].product.price == 20.75
    assert "atípico" in rej[0].reason


def test_poucos_itens_nao_filtra():
    items = [_item(p, i) for i, p in enumerate([300, 400, 20])]
    ok, rej = split_outliers(items)
    assert len(ok) == 3 and rej == []


def test_precos_parecidos_nao_rejeita_nada():
    items = [_item(p, i) for i, p in enumerate([300, 320, 350, 400, 420, 450, 470, 500, 520])]
    ok, rej = split_outliers(items)
    assert len(ok) == 9 and rej == []