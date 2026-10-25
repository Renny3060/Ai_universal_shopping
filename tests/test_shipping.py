from backend.agents.group3_logic.financial_agent import apply_costs
from backend.schemas.product import ProductResult

CFG = {"pcdiga": {"free_shipping_over": 524.90}}


def prod(price, store="pcdiga"):
    return ProductResult(store=store, external_id="1", title="Placa Gráfica X",
                         url="https://www.pcdiga.com/1", price=price)


def test_no_limiar_observado_portes_zero():
    item = apply_costs([prod(524.90)], CFG)[0]
    assert item.shipping == 0.0
    assert item.total_cost == 524.90
    assert not any("Portes desconhecidos" in w for w in item.warnings)


def test_abaixo_do_limiar_portes_desconhecidos():
    item = apply_costs([prod(449.90)], CFG)[0]
    assert item.shipping is None
    assert any("Portes desconhecidos" in w for w in item.warnings)


def test_valor_fixo_quando_nao_e_gratis():
    cfg = {"pcdiga": {"free_shipping_over": 100, "shipping_flat": 3.9}}
    item = apply_costs([prod(30.0)], cfg)[0]
    assert item.shipping == 3.9
    assert item.total_cost == 33.9