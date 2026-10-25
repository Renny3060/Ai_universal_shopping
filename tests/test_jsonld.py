import json

from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.jsonld import extract_products


def html_with(*blocks):
    scripts = "".join(
        f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blocks
    )
    return f"<html><head>{scripts}</head><body></body></html>"


def product(name, price, **extra):
    d = {"@type": "Product", "name": name, "url": f"/p/{name}", "sku": f"sku-{name}",
         "offers": {"@type": "Offer", "priceCurrency": "EUR", "price": price}}
    d.update(extra)
    return d


def test_item_list_com_produtos():
    data = {"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "item": product("a", "100.50")},
        {"@type": "ListItem", "position": 2, "item": product("b", 20)},
    ]}
    items = extract_products(html_with(data), "https://shop.test")
    assert [(i["title"], i["price"]) for i in items] == [("a", 100.5), ("b", 20.0)]
    assert items[0]["url"] == "https://shop.test/p/a"
    assert items[0]["external_id"] == "sku-a"


def test_graph_e_lista_de_blocos():
    data = {"@graph": [{"@type": "WebPage"}, product("g", "9,99")]}
    items = extract_products(html_with(data, product("x", "5")), "https://s.test")
    assert sorted(i["title"] for i in items) == ["g", "x"]
    assert [i for i in items if i["title"] == "g"][0]["price"] == 9.99


def test_ignora_aggregate_offer_e_preco_zero():
    agg = {"@type": "Product", "name": "Resultados", "url": "/s",
           "offers": {"@type": "AggregateOffer", "lowPrice": "0", "highPrice": "7299"}}
    zero = product("z", "0")
    assert extract_products(html_with(agg, zero), "https://s.test") == []


def test_fora_de_stock():
    p = product("o", "50")
    p["offers"]["availability"] = "https://schema.org/OutOfStock"
    assert extract_products(html_with(p), "https://s.test")[0]["in_stock"] is False


def test_json_invalido_e_sem_json_ld():
    bad = '<script type="application/ld+json">{nao e json</script>'
    assert extract_products(f"<html><head>{bad}</head></html>") == []
    assert extract_products("<html></html>") == []


def test_dedupe_por_url():
    items = extract_products(html_with(product("a", "10"), product("a", "10")), "https://s.test")
    assert len(items) == 1


def test_scraper_sem_card_usa_json_ld():
    cfg = {"search_url": "https://shop.test/s?q={q}", "base_url": "https://shop.test", "country": "PT"}
    scraper = ConfigurableScraper("shop", cfg)
    assert scraper.wait_selector == 'script[type="application/ld+json"]'
    items = scraper.parse(html_with(product("Placa Recondicionado", "300")))
    assert len(items) == 1
    assert items[0].store == "shop"
    assert items[0].price == 300.0
    assert items[0].condition == "refurbished"