from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES

CARD = """
<div data-cy="l-card" data-testid="l-card" id="{id}">
  <a data-testid="card-title-link" href="/d/anuncio/{slug}.html?search_reason=search">
    <h4>{title}</h4></a>
  <img src="https://img.example/{id}.jpg"/>
  <p data-testid="ad-price">{price}<span>Negociável</span></p>
</div>
"""


def _html(*cards):
    return "<html><body>" + "".join(CARD.format(**c) for c in cards) + "</body></html>"


def _scraper():
    return ConfigurableScraper("olx", STORES["olx"])


def test_olx_parse_usado_por_defeito_e_ignora_troca():
    html = _html(
        {"id": "1", "slug": "a", "title": "MSI GeForce RTX 5060 8G Shadow 2X", "price": "300 €"},
        {"id": "2", "slug": "b", "title": "PC Gaming RTX 5060", "price": "1.025 €"},
        {"id": "3", "slug": "c", "title": "Placa a troca", "price": "Troca"},
    )
    items = _scraper().parse(html)
    assert [i.external_id for i in items] == ["1", "2"]
    assert [i.price for i in items] == [300.0, 1025.0]
    assert all(i.condition == "used" for i in items)
    assert items[0].url == "https://www.olx.pt/d/anuncio/a.html?search_reason=search"


def test_olx_recondicionado_no_titulo_mantem_se():
    html = _html({"id": "9", "slug": "z", "title": "RTX 5060 recondicionada", "price": "250 €"})
    assert _scraper().parse(html)[0].condition == "refurbished"


def test_olx_urls_com_slug():
    s = _scraper()
    assert s.build_url("rtx 5060") == "https://www.olx.pt/ads/q-rtx-5060/"
    assert s.build_url("Placa Gráfica RTX 5060") == "https://www.olx.pt/ads/q-placa-grafica-rtx-5060/"
    assert s.build_page_url("rtx 5060", 2) == "https://www.olx.pt/ads/q-rtx-5060/?page=2"


def test_lojas_sem_q_sep_continuam_com_quote_plus():
    p = ConfigurableScraper("worten", STORES["worten"])
    assert p.build_url("rtx 5060") == "https://www.worten.pt/search?query=rtx+5060"