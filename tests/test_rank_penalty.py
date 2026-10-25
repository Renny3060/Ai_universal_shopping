from backend.agents.group2_search.stores import STORES
from backend.agents.group3_logic.scoring_agent import rank
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def _item(store, price):
    p = ProductResult(store=store, external_id=store, title="Portatil 16GB", url="https://x.pt/1", price=price)
    return RankedProduct(product=p, shipping=None, taxes=0.0, total_cost=price,
                         category=None, score=0.0, warnings=[])


def test_penalizacao_passa_loja_para_baixo_em_best_value():
    items = [_item("aliexpress", 150.0), _item("pcdiga", 155.0)]
    assert rank(list(items))[0].product.store == "aliexpress"
    out = rank([_item("aliexpress", 150.0), _item("pcdiga", 155.0)], "best_value", {"aliexpress": 25.0})
    assert out[0].product.store == "pcdiga"


def test_cheapest_ignora_penalizacao():
    out = rank([_item("aliexpress", 150.0), _item("pcdiga", 300.0)], "cheapest", {"aliexpress": 25.0})
    assert out[0].product.store == "aliexpress"


def test_score_nao_fica_negativo():
    out = rank([_item("aliexpress", 150.0)], "best_value", {"aliexpress": 500.0})
    assert out[0].score == 0.0


def test_aliexpress_tem_penalizacao_configurada():
    assert STORES["aliexpress"]["rank_penalty"] == 25.0


def test_penalizacao_nao_vence_diferenca_de_preco_grande():
    out = rank([_item("aliexpress", 150.0), _item("pcdiga", 300.0)], "best_value", {"aliexpress": 25.0})
    assert out[0].product.store == "aliexpress"
