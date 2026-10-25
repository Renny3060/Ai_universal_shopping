from backend.agents.group2_search import base_scraper
from backend.agents.group2_search.configurable_scraper import ConfigurableScraper

BASE_CFG = {
    "search_url": "https://shop.test/s?q={q}",
    "base_url": "https://shop.test",
    "card": "div.card",
    "title": "h3",
    "price": ".p",
    "link": "a",
}
PAGED_CFG = dict(BASE_CFG, page_url="https://shop.test/s?q={q}&page={page}")


def page(*names):
    return "".join(
        f'<div class="card"><h3>{n}</h3><span class="p">100,00 €</span><a href="/{n}">x</a></div>'
        for n in names
    )


def setup(monkeypatch, pages):
    """pages: dict URL -> HTML. Devolve a lista de URLs pedidos."""
    calls: list[str] = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        return pages.get(url, "")

    monkeypatch.setattr(base_scraper, "fetch_html", fake_fetch)
    monkeypatch.setattr(base_scraper, "get_cached", lambda key: None)
    monkeypatch.setattr(base_scraper, "set_cached", lambda *a, **k: None)
    return calls


def test_le_duas_paginas(monkeypatch):
    calls = setup(monkeypatch, {
        "https://shop.test/s?q=rtx+5060": page("a", "b"),
        "https://shop.test/s?q=rtx+5060&page=2": page("c"),
    })
    items = ConfigurableScraper("shop", PAGED_CFG).search("rtx 5060", max_pages=2)
    assert [i.title for i in items] == ["a", "b", "c"]
    assert len(calls) == 2


def test_para_quando_a_pagina_so_tem_repetidos(monkeypatch):
    calls = setup(monkeypatch, {
        "https://shop.test/s?q=x": page("a", "b"),
        "https://shop.test/s?q=x&page=2": page("a", "b"),
    })
    items = ConfigurableScraper("shop", PAGED_CFG).search("x", max_pages=3)
    assert len(items) == 2
    assert len(calls) == 2


def test_para_quando_a_pagina_vem_vazia(monkeypatch):
    calls = setup(monkeypatch, {"https://shop.test/s?q=x": page("a")})
    items = ConfigurableScraper("shop", PAGED_CFG).search("x", max_pages=3)
    assert len(items) == 1
    assert len(calls) == 2


def test_sem_page_url_so_le_a_primeira(monkeypatch):
    calls = setup(monkeypatch, {"https://shop.test/s?q=x": page("a")})
    items = ConfigurableScraper("shop", BASE_CFG).search("x", max_pages=3)
    assert len(items) == 1
    assert len(calls) == 1