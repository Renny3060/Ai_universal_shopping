from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES

CARD = """
<a class="us--container--x search-card-item" href="{href}">
  <img class="product-img" src="//ae-pic.example/{n}.jpg"/>
  <h3>{title}</h3>
  <div aria-label="{label}"><div><span>{p1}</span><span>,</span><span>{p2}</span><span>€</span></div></div>
</a>
"""


def _html(*cards):
    return "<html><body>" + "".join(CARD.format(**c) for c in cards) + "</body></html>"


def _scraper():
    return ConfigurableScraper("aliexpress", STORES["aliexpress"])


def test_aliexpress_parse_id_url_e_preco():
    html = _html(
        {"href": "//pt.aliexpress.com/item/1005011726112437.html?algo_pvid=abc&x=1", "n": 1,
         "title": "Placa gráfica RTX 5060 8GB", "label": "699,95€", "p1": "699", "p2": "95"},
    )
    items = _scraper().parse(html)
    assert len(items) == 1
    it = items[0]
    assert it.external_id == "1005011726112437"
    assert it.url == "https://pt.aliexpress.com/item/1005011726112437.html"
    assert it.price == 699.95
    assert it.condition == "new"
    assert it.image_url == "https://ae-pic.example/1.jpg"


def test_aliexpress_milhares_em_spans():
    html = _html(
        {"href": "//pt.aliexpress.com/item/1.html", "n": 1, "title": "PC RTX 5060 Ti",
         "label": "1.258,66€", "p1": "1</span><span>.</span><span>258", "p2": "66"},
    )
    assert _scraper().parse(html)[0].price == 1258.66


def test_aliexpress_id_estavel_sem_padrao_de_item():
    h1 = "https://www.aliexpress.com/ssr/300000512/BundleDeals?algo_pvid=aaa"
    h2 = "https://www.aliexpress.com/ssr/300000512/BundleDeals?algo_pvid=bbb"
    base = {"n": 2, "title": "Bundle RTX 5060", "label": "500,00€", "p1": "500", "p2": "00"}
    a = _scraper().parse(_html({**base, "href": h1}))[0]
    b = _scraper().parse(_html({**base, "href": h2}))[0]
    assert a.external_id == b.external_id
    assert a.url == "https://www.aliexpress.com/ssr/300000512/BundleDeals"


def test_aliexpress_url_de_pesquisa():
    assert _scraper().build_url("rtx 5060") == "https://pt.aliexpress.com/w/wholesale-rtx-5060.html"

def test_aliexpress_url_pagina_2():
    assert _scraper().build_page_url("rtx 5060", 2) == (
        "https://pt.aliexpress.com/w/wholesale-rtx-5060.html?page=2&g=y&SearchText=rtx+5060"
    )