from backend.agents.group3_logic import validator_agent as v
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct
from backend.schemas.search import ProductSpecs, Requirement


def _item(title):
    p = ProductResult(store="x", external_id="1", title=title,
                      url="https://x.com/1", price=100.0)
    return RankedProduct(product=p, total_cost=100.0)


def _specs(*reqs):
    return ProductSpecs(category="", requirements=list(reqs))


def _req(attr, value):
    return Requirement(attribute=attr, operator="contains", value=value)


def test_product_type_nao_gera_aviso():
    specs = _specs(_req("product_type", "golf gti"))
    ok, _ = v.validate([_item("VW Golf V 2.0 TDI")], None, None, specs)
    assert ok[0].warnings == []


def test_atributo_igual_ao_valor_nao_gera_aviso():
    specs = _specs(_req("modular", "modular"))
    ok, _ = v.validate([_item("Capacete NOLAN N90")], None, None, specs)
    assert ok[0].warnings == []


def test_requisito_real_continua_a_gerar_aviso():
    specs = _specs(_req("gpu", "RTX 5060"))
    ok, _ = v.validate([_item("Placa Gráfica Asus")], None, None, specs)
    assert any("Não confirmado" in w for w in ok[0].warnings)