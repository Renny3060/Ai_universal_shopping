from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group3_logic.financial_agent import apply_costs
from backend.schemas.product import ProductResult

CFG = {
    "search_url": "https://shop.test/s?q={q}",
    "base_url": "https://shop.test",
    "card": "article.c",
    "title_attr": "data-name",
    "price_attr": "data-price",
    "id_attr": "data-id",
    "link": "a",
}


def card(*spans):
    inner = "".join(f"<span>{s}</span>" for s in spans)
    return (f'<article class="c" data-name="Placa A" data-price="100" data-id="1">'
            f'<a href="/a">x</a>{inner}</article>')


def parse(html, **extra):
    return ConfigurableScraper("shop", dict(CFG, **extra)).parse(html)


def test_vendedor_em_blocos_separados():
    items = parse(card("Vendido por", "LojaWeb", "Comparar"), seller_label="Vendido por")
    assert items[0].seller_name == "LojaWeb"


def test_vendedor_no_mesmo_bloco():
    items = parse(card("Vendido por: Outra Loja"), seller_label="Vendido por")
    assert items[0].seller_name == "Outra Loja"


def test_sem_etiqueta_no_cartao():
    assert parse(card("Comparar"), seller_label="Vendido por")[0].seller_name is None


def test_sem_seller_label_na_config():
    assert parse(card("Vendido por", "LojaWeb"))[0].seller_name is None


def prod(seller):
    return ProductResult(store="worten", external_id="1", title="Placa", price=464.41,
                         url="https://www.worten.pt/produtos/x", seller_name=seller)


def _vendor_warnings(seller):
    cfg = {"worten": {"own_seller_names": ["worten"]}}
    return [w for w in apply_costs([prod(seller)], cfg)[0].warnings if "Vendido por" in w]


def test_aviso_de_vendedor_externo():
    ws = _vendor_warnings("LojaWeb")
    assert len(ws) == 1 and "LojaWeb" in ws[0]


def test_sem_aviso_se_vendedor_e_a_propria_loja():
    assert _vendor_warnings("Worten") == []


def test_sem_aviso_se_vendedor_desconhecido():
    assert _vendor_warnings(None) == []