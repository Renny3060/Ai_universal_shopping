from backend.agents.group3_logic.dedupe import dedupe
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def item(ext_id, title, price, store="worten"):
    p = ProductResult(store=store, external_id=ext_id, title=title,
                      url=f"https://example.com/{ext_id}", price=price)
    return RankedProduct(product=p, total_cost=price)


def test_junta_iguais_e_avisa():
    out = dedupe([item("1", "Portátil Vanwin 15.6", 329.99),
                  item("2", "Portátil Vanwin 15.6", 329.99),
                  item("3", "Portátil Vanwin 15.6", 329.99)])
    assert len(out) == 1
    assert out[0].product.external_id == "1"
    assert "3 listagens iguais" in out[0].warnings[0]


def test_ignora_maiusculas_e_espacos():
    out = dedupe([item("1", "Portátil VANWIN  15.6.", 329.99),
                  item("2", "portátil vanwin 15.6", 329.99)])
    assert len(out) == 1


def test_preco_diferente_nao_junta():
    assert len(dedupe([item("1", "Portátil X", 300), item("2", "Portátil X", 310)])) == 2


def test_loja_diferente_nao_junta():
    assert len(dedupe([item("1", "Portátil X", 300, "worten"),
                       item("2", "Portátil X", 300, "pcdiga")])) == 2


def test_sem_repetidos_nao_acrescenta_aviso():
    out = dedupe([item("1", "Portátil A", 300), item("2", "Portátil B", 310)])
    assert [i.warnings for i in out] == [[], []]