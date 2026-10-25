from backend.agents.group2_search.discovery import (
    clean_tracking, price_card_candidates, store_entry, template_from_url,
)


def test_template_com_mais_e_sem_tracking():
    url = "https://www.loja.pt/search?query=rtx+5060&srsltid=abc&utm_source=x&gclid=1"
    assert template_from_url(url, "rtx 5060") == ("https://www.loja.pt/search?query={q}", None)


def test_template_com_slug_no_caminho():
    assert template_from_url("https://www.olx.pt/ads/q-rtx-5060/", "rtx 5060") == (
        "https://www.olx.pt/ads/q-{q}/", "-")


def test_template_ignora_maiusculas_e_percent20():
    assert template_from_url("https://x.pt/pesquisa/RTX%205060?page=1", "rtx 5060") == (
        "https://x.pt/pesquisa/{q}?page=1", None)


def test_template_sem_termo_no_url():
    assert template_from_url("https://x.pt/home", "rtx 5060") is None
    assert template_from_url("https://x.pt/s?q=rtx+5060", "") is None


def test_clean_tracking():
    assert clean_tracking("https://m.com/pt/?gad_source=1&gclid=a&b=2#x") == "https://m.com/pt/?b=2"


def test_price_card_candidates_encontra_cartoes_repetidos():
    card = '<li data-testid="card"><h3>Produto {n}</h3><span>{n}50 €</span></li>'
    html = "<html><body><ul>" + "".join(card.format(n=i) for i in range(1, 7)) + "</ul></body></html>"
    sigs = dict(price_card_candidates(html))
    assert sigs["li[data-testid='card']"] == 6


def test_store_entry():
    text = store_entry("olx", "https://www.olx.pt/ads/q-rtx-5060/", "https://www.olx.pt/ads/q-{q}/", "-")
    assert '"q_sep": "-"' in text and '"base_url": "https://www.olx.pt"' in text
    assert "q_sep" not in store_entry("x", "https://x.pt/s?q=a", "https://x.pt/s?q={q}", None)