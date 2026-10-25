from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES

CARD = """
<div data-component-type="s-search-result" data-asin="{asin}">
  <h2><span>{title}</span></h2>
  <img class="s-image" src="https://m.media-amazon.com/images/{asin}.jpg"/>
  {price_html}
  <a href="{href}">ver</a>
</div>
"""
PRICE = '<span class="a-price"><span class="a-offscreen">{p}</span><span aria-hidden="true">x</span></span>'


def _html(*cards):
    out = []
    for c in cards:
        price_html = PRICE.format(p=c["price"]) if c.get("price") else ""
        out.append(CARD.format(asin=c["asin"], title=c["title"], href=c["href"], price_html=price_html))
    return "<html><body>" + "".join(out) + "</body></html>"


def _scraper():
    return ConfigurableScraper("amazon_es", STORES["amazon_es"])


def test_amazon_url_canonico_id_e_preco():
    html = _html({"asin": "B09729YMPT", "title": "MSI GeForce RTX 5060 8G Shadow 2X OC",
                  "price": "487,93\u00a0€", "href": "/-/pt/dp/B09729YMPT/ref=sr_1_1?dib=abc"})
    it = _scraper().parse(html)[0]
    assert it.external_id == "B09729YMPT"
    assert it.url == "https://www.amazon.es/dp/B09729YMPT"
    assert it.price == 487.93
    assert it.condition == "new"
    assert it.image_url.endswith("B09729YMPT.jpg")


def test_amazon_patrocinado_usa_o_asin_e_nao_o_redirecionamento():
    html = _html({"asin": "B0CSYB78NH", "title": "Placa gráfica RTX 5060",
                  "price": "99,00\u00a0€", "href": "/-/pt/sspa/click?ie=UTF8&spc=abc"})
    assert _scraper().parse(html)[0].url == "https://www.amazon.es/dp/B0CSYB78NH"


def test_amazon_sem_preco_e_ignorado():
    html = _html(
        {"asin": "A1", "title": "RTX 5060 sem preço", "price": None, "href": "/dp/A1"},
        {"asin": "A2", "title": "RTX 5060 com preço", "price": "400,00\u00a0€", "href": "/dp/A2"},
    )
    assert [i.external_id for i in _scraper().parse(html)] == ["A2"]


def test_amazon_reacondicionado():
    html = _html({"asin": "A3", "title": "RTX 5060 Reacondicionado", "price": "300,00\u00a0€", "href": "/dp/A3"})
    assert _scraper().parse(html)[0].condition == "refurbished"


def test_amazon_urls_de_pesquisa():
    s = _scraper()
    assert s.build_url("rtx 5060") == "https://www.amazon.es/s?k=rtx+5060"
    assert s.build_page_url("rtx 5060", 2) == "https://www.amazon.es/s?k=rtx+5060&page=2"