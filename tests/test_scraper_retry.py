import pytest

from backend.agents.group2_search import base_scraper
from backend.agents.group2_search.base_scraper import ScrapeBlocked
from backend.agents.group2_search.configurable_scraper import ConfigurableScraper

CFG = {
    "search_url": "https://shop.test/s?q={q}",
    "base_url": "https://shop.test",
    "card": "div.card",
    "title": "h3",
    "price": ".p",
    "link": "a",
    "page_url": "https://shop.test/s?q={q}&page={page}",
}

EMPTY_OK = "<html><head><title>Resultados</title></head><body>" + "<p>sem resultados</p>" * 40 + "</body></html>"
BLOCKED = "<html><head><title>Just a moment...</title></head><body>" + "x" * 600 + "</body></html>"


def page(*names):
    return "".join(
        f'<div class="card"><h3>{n}</h3><span class="p">100,00 €</span><a href="/{n}">x</a></div>'
        for n in names
    )


def setup(monkeypatch, responses):
    """responses: lista de HTML (ou Exception) devolvidos por ordem; o último repete-se."""
    calls: list[str] = []
    sleeps: list[float] = []
    seq = list(responses)

    def fake_fetch(url, **kwargs):
        calls.append(url)
        r = seq.pop(0) if len(seq) > 1 else seq[0]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(base_scraper, "fetch_html", fake_fetch)
    monkeypatch.setattr(base_scraper, "_sleep", sleeps.append)
    monkeypatch.setattr(base_scraper, "get_cached", lambda key: None)
    monkeypatch.setattr(base_scraper, "set_cached", lambda *a, **k: None)
    return calls, sleeps


def test_repete_apos_excecao_e_recupera(monkeypatch):
    calls, sleeps = setup(monkeypatch, [TimeoutError("timeout"), page("a", "b")])
    items = ConfigurableScraper("shop", CFG).search("x")
    assert [i.title for i in items] == ["a", "b"]
    assert len(calls) == 2
    assert sleeps == [4.0]


def test_repete_pagina_limpa_sem_produtos_e_recupera(monkeypatch):
    calls, sleeps = setup(monkeypatch, [EMPTY_OK, page("a")])
    items = ConfigurableScraper("shop", CFG).search("x")
    assert len(items) == 1
    assert len(calls) == 2


def test_pagina_limpa_sem_produtos_so_repete_uma_vez(monkeypatch):
    calls, sleeps = setup(monkeypatch, [EMPTY_OK])
    items = ConfigurableScraper("shop", CFG).search("x")
    assert items == []
    assert len(calls) == 2
    assert len(sleeps) == 1


def test_bloqueio_persistente_levanta_erro_depois_de_3_tentativas(monkeypatch):
    calls, sleeps = setup(monkeypatch, [BLOCKED])
    with pytest.raises(ScrapeBlocked, match="bloqueado"):
        ConfigurableScraper("shop", CFG).search("x")
    assert len(calls) == 3
    assert sleeps == [4.0, 10.0]


def test_excecao_persistente_na_pagina_1_sobe(monkeypatch):
    calls, _ = setup(monkeypatch, [TimeoutError("timeout")])
    with pytest.raises(TimeoutError):
        ConfigurableScraper("shop", CFG).search("x")
    assert len(calls) == 3


def test_falha_na_pagina_2_mantem_a_pagina_1(monkeypatch):
    calls, sleeps = setup(monkeypatch, [page("a", "b"), RuntimeError("falhou")])
    items = ConfigurableScraper("shop", CFG).search("x", max_pages=2)
    assert [i.title for i in items] == ["a", "b"]
    assert len(calls) == 2          # a página 2 não tem repetições
    assert sleeps == []


def test_pagina_2_vazia_nao_repete(monkeypatch):
    calls, sleeps = setup(monkeypatch, [page("a"), EMPTY_OK])
    items = ConfigurableScraper("shop", CFG).search("x", max_pages=2)
    assert len(items) == 1
    assert len(calls) == 2
    assert sleeps == []