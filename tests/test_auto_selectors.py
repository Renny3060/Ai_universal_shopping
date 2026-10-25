from backend.agents.group2_search.auto_selectors import (
    entry_text, is_euro_country, merge_stores, propose, store_slug, term_in_html, vertical_for,
)


def _card(i, old=None):
    old_html = f'<span class="old-price">{old} €</span>' if old else ""
    return (f'<li class="product-item"><a href="/p/{i}"><h3>Produto numero {i} SSD</h3></a>'
            f'{old_html}<span class="price">{10 + i},90 €</span></li>')


def _page(n=8, old=None):
    return "<html><body><ul>" + "".join(_card(i, old) for i in range(n)) + "</ul></body></html>"


def test_propose_encontra_cartao_titulo_preco_link():
    p = propose(_page())
    assert p is not None
    assert p["card"] == "li.product-item"
    assert p["n_cards"] == 8
    assert p["title"] == "h3 a" or p["title"] == "h3"
    assert p["price"].endswith("price")
    assert p["cov_title"] == 1.0 and p["cov_price"] == 1.0


def test_propose_ignora_preco_antigo_riscado():
    p = propose(_page(old=99))
    assert p is not None
    assert "old" not in p["price"]


def test_propose_sem_precos_devolve_none():
    assert propose("<html><body><ul><li>nada</li></ul></body></html>") is None


def test_propose_poucos_cartoes_devolve_none():
    assert propose(_page(n=3)) is None


def test_term_in_html():
    assert term_in_html("<title>Pesquisa por ssd 1tb</title>", "SSD 1TB")
    assert not term_in_html("<title>Início</title>", "ssd 1tb")


def test_store_slug_e_vertical():
    assert store_slug("Império Multimédia") == "imperio_multimedia"
    assert vertical_for("moto") == ["moto"]
    assert vertical_for("hardware") == ["tech"]
    assert vertical_for("moda") == ["general"]
    assert vertical_for("auto") == ["general"]   # peças/acessórios: fora das pesquisas de carros


def test_so_paises_com_euro():
    assert is_euro_country("pt") and is_euro_country("ES") and is_euro_country("DE")
    assert not is_euro_country("US") and not is_euro_country("GB") and not is_euro_country("PL")
    assert not is_euro_country("")


def test_merge_nao_substitui_nem_inventa():
    existing = {"a": {"x": 1}}
    generated = {"a": {"x": 2}, "b": {"x": 3}}
    merged, added, skipped = merge_stores(existing, generated, ["a", "b", "c"])
    assert merged == {"a": {"x": 1}, "b": {"x": 3}}
    assert added == ["b"]
    assert skipped == ["a", "c"]


def test_entry_text_gera_python_valido_com_booleanos():
    cfg = {"search_url": "https://x.pt/s?q={q}", "card": "div[data-id='a']", "verticals": ["tech", "cars"],
           "default_condition": "used", "private_listings": True}
    code = "AUTO = {\n" + entry_text("loja", cfg) + "\n}"
    ns = {}
    exec(code, ns)
    assert ns["AUTO"]["loja"] == cfg
