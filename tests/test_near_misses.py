from backend.agents.group3_logic.near_misses import near_misses
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RejectedProduct


def _r(title, price, reason, url=None):
    p = ProductResult(store="olx", title=title, price=price, url=url or f"https://www.olx.pt/{title}",
                      external_id=title)
    return RejectedProduct(product=p, reason=reason)


def test_so_criterios_moles_e_dentro_do_orcamento():
    rej = [
        _r("Portátil Gaming HP Omen RTX 4060", 999, "marca diferente (hp; pedido: asus ou lenovo)"),
        _r("Portátil Gaming Lenovo LOQ RTX 4060", 421, "abaixo do orçamento mínimo (800 €)"),
        _r("Portátil Gaming Asus RTX 4060", 1500, "estado diferente (usado; pedido: novo)"),
        _r("Portátil Gaming MSI RTX 4060", 900, "acima do orçamento"),
        _r("SSD 1TB Kingston", 60, "estado diferente (usado; pedido: novo)"),
    ]
    out = near_misses(rej, "laptop", max_budget=1200)
    assert [r.product.price for r in out] == [421, 999]


def test_limite_e_duplicados():
    rej = [_r(f"Portátil A{i}", 100 + i, "marca diferente (hp; pedido: asus)") for i in range(20)]
    rej.append(rej[0])
    assert len(near_misses(rej, None, limit=5)) == 5


def test_ordem_por_distancia_ao_intervalo():
    rej = [
        _r("Portátil Gaming Lenovo A", 421, "abaixo do orçamento mínimo (800 €)"),
        _r("Portátil Gaming Lenovo B", 799.97, "abaixo do orçamento mínimo (800 €)"),
        _r("Portátil Gaming Asus C", 1100, "estado diferente (usado; pedido: novo)"),
    ]
    out = near_misses(rej, "laptop", max_budget=1200, min_budget=800)
    assert [r.product.price for r in out] == [1100, 799.97, 421]
