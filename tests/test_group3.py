from backend.agents.group3_logic.categories import classify_title, infer_wanted_category
from backend.agents.group3_logic.financial_agent import apply_costs
from backend.agents.group3_logic.scoring_agent import rank
from backend.agents.group3_logic.validator_agent import validate
from backend.schemas.product import ProductResult
from backend.services.tax_calculator import calc_taxes


def prod(title, price, store="pcdiga", condition="new"):
    return ProductResult(store=store, external_id=title[:8], title=title,
                         url="http://x", price=price, condition=condition)


def test_taxes():
    assert calc_taxes(100, 0, "PT")[0] == 0.0
    assert calc_taxes(100, 0, "NON_EU")[0] == 23.0
    assert calc_taxes(200, 0, "NON_EU")[0] == 46.0


def test_categories():
    assert classify_title("Portátil Gaming ASUS TUF RTX 5060 RAM 32GB") == "laptop"
    assert classify_title('Placa Gráfica MSI GeForce RTX 5060 "Blackwell"') == "graphics_card"
    assert infer_wanted_category("rtx 5060") == "graphics_card"
    assert infer_wanted_category("pc gaming rtx 4060") == "desktop_pc"
    assert infer_wanted_category("auscultadores bluetooth") is None


def test_validator_rejects_laptop_and_budget():
    items = apply_costs([
        prod("Placa Gráfica Asus RTX 5060", 450),
        prod("Placa Gráfica Gigabyte RTX 5060 Ti", 900),
        prod("Portátil ASUS TUF RTX 5060", 1899),
    ], {})
    ok, rejected = validate(items, "graphics_card", 600)
    assert len(ok) == 1
    assert {r.reason for r in rejected} == {"categoria diferente (laptop)", "acima do orçamento"}


def test_unknown_shipping_warns():
    item = apply_costs([prod("Placa Gráfica X", 100)], {})[0]
    assert item.shipping is None
    assert any("Portes" in w for w in item.warnings)


def test_shipping_rules_and_ranking():
    cfg = {"pcdiga": {"shipping_flat": 5.0, "free_shipping_over": 200.0}}
    items = apply_costs([prod("A", 100), prod("B", 250), prod("C", 90, condition="refurbished")], cfg)
    assert items[0].total_cost == 105.0
    assert items[1].total_cost == 250.0
    assert rank(items, "cheapest")[0].product.title == "C"
    assert rank(items, "best_value")[0].score >= rank(items, "best_value")[-1].score