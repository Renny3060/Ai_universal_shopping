import pytest

from backend.agents.group3_logic.relevance_rules import query_words, reason_for, split_not_the_item
from backend.agents.group3_logic.financial_agent import apply_costs
from backend.schemas.product import ProductResult


@pytest.mark.parametrize("query,title", [
    ("audi tt até 5000€", "Carro de brinquedo Audi TT 1:32 metal"),
    ("audi tt até 5000€", "Miniatura Audi TT RS escala 1:18"),
    ("audi tt", "Audi TT 1/18 Maisto"),
    ("audi tt", "Poster Audi TT"),
    ("monitor 24 polegadas até 150€", "Mala Portátil para Monitor 24 Polegadas"),
    ("ssd 1tb até 100€", "Cartão de Expansão Cf Para Ssd M2 Adaptador"),
    ("iphone 15", "Capa para iPhone 15 Pro"),
    ("bicicleta", "Cesto para bicicleta"),
])
def test_rejects(query, title):
    assert reason_for(title, query) is not None


@pytest.mark.parametrize("query,title", [
    ("audi tt até 5000€", "Audi TT Coupe 2.0 TFSI 2008"),
    ("monitor 24 polegadas", "Monitor 24 polegadas Full HD para escritório"),
    ("monitor 27", "Monitor LG 27 IPS 16:9"),
    ("monitor 34", "Monitor Curvo 21:9 34 polegadas"),
    ("memória RAM 16GB DDR4", "Memória RAM Kingston 16GB DDR4 para portátil"),
    ("ssd 1tb", "SSD Kingston 1TB NVMe para PC"),
    ("lego ninjago", "Lego Ninjago Set 71799"),
    ("capa iphone 15", "Capa para iPhone 15 Pro"),
    ("carro telecomandado", "Carro telecomandado 4x4"),
    ("miniatura audi tt", "Miniatura Audi TT RS escala 1:18"),
])
def test_keeps(query, title):
    assert reason_for(title, query) is None


def test_general_vertical_allows_toys():
    assert reason_for("Peluche urso", "peluche", "general") is None
    assert reason_for("Boneca Barbie", "barbie", "general") is None
    assert reason_for("Boneca Barbie", "barbie", "tech") is not None


def test_query_words_ignore_budget_and_stopwords():
    assert query_words("audi tt até 5000€") == ["audi"]
    assert query_words("memória RAM para portátil até 60€") == ["memoria", "ram", "portatil"]


def test_split_and_no_text():
    items = apply_costs([
        ProductResult(store="olx", title="Carro de brinquedo Audi TT", price=15, url="https://www.olx.pt/d/1", external_id="1"),
        ProductResult(store="olx", title="Audi TT 1.8 T", price=4500, url="https://www.olx.pt/d/2", external_id="2"),
    ], {})
    ok, out = split_not_the_item(items, "audi tt até 5000€")
    assert [i.product.title for i in ok] == ["Audi TT 1.8 T"]
    assert out[0].reason.startswith("não é o artigo pedido")
    ok2, out2 = split_not_the_item(items, "")
    assert len(ok2) == 2 and out2 == []
