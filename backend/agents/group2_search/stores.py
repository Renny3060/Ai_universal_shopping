# Configuração por loja. Seletores confirmados com scripts/inspect_store.py e analyze_html.py.
# search_url: faz a pesquisa no browser, copia o URL e troca o termo por {q}
# use_hint: se True, acrescenta ao termo a palavra da categoria (ex.: "placa grafica").
#           Testado: a Worten precisa dela; a PCDiga perde produtos com ela.
# free_shipping_over: preço a partir do qual o envio foi observado como grátis (0,00 €) no carrinho.
#           É uma observação, não a regra publicada da loja. Abaixo disto os portes ficam
#           desconhecidos (aviso), até haver mais observações.

STORES = {
    "pcdiga": {
        "search_url": "https://www.pcdiga.com/search?query={q}",
        "base_url": "https://www.pcdiga.com",
        "card": "div.product-list div.bg-background-off",
        "title": "h3",
        "price": ".price_special_price_wrapper p",
        "link": "a[href]",
        "image": "img",
        "country": "PT",
        "use_hint": False,
        "page_url": "https://www.pcdiga.com/search?query={q}&page={page}",
        "verticals": ["tech"],
        # observado no carrinho: grátis a 84,90 € (aspirador) e a 524,90 € (Asus RTX 5060).
        # A loja diz "consoante tipo e volume de encomenda": o limiar exato não é conhecido.
    },
    "worten": {
        "search_url": "https://www.worten.pt/search?query={q}",
        "base_url": "https://www.worten.pt",
        "card": "article.product-card",
        "wait": "article.product-card",
        "title_attr": "data-cnstrc-item-name",
        "price_attr": "data-cnstrc-item-price",
        "id_attr": "data-cnstrc-item-id",
        "link": "a[href^='/produtos/']",
        "image": "img.product-card__image",
        "country": "PT",
        "use_hint": True,
        "seller_label": "Vendido por",
        "own_seller_names": ["worten"],
        "page_url": "https://www.worten.pt/search?query={q}&page={page}",
        "verticals": ["tech"],
        # Sem valor de portes: dependem do vendedor. Observado (sem sessão iniciada):
        # Zotac RTX 5060 Solo, 464,41 €, vendida por LOJAWEB, envio estimado 6,90 €.
    },
    "olx": {
        "search_url": "https://www.olx.pt/ads/q-{q}/",
        "page_url": "https://www.olx.pt/ads/q-{q}/?page={page}",
        "base_url": "https://www.olx.pt",
        "q_sep": "-",
        "card": "div[data-testid='l-card']",
        "title": "h4",
        "price": "[data-testid='ad-price']",
        "link": "a[data-testid='card-title-link']",
        "image": "img",
        "id_attr": "id",
        "country": "PT",
        "use_hint": False,
        "default_condition": "used",
        "extra_domains": ["standvirtual.com"],
        "verticals": ["tech", "general", "cars", "moto"],
        "private_listings": True,
    },
    "aliexpress": {
        "page_url": "https://pt.aliexpress.com/w/wholesale-{q}.html?page={page}&g=y&SearchText={qp}",
        "search_url": "https://pt.aliexpress.com/w/wholesale-{q}.html",
        "base_url": "https://pt.aliexpress.com",
        "q_sep": "-",
        "card": "a.search-card-item",
        "title": "h3",
        "price": "div[aria-label$='€']",
        "image": "img.product-img",
        "id_regex": r"/item/(\d+)\.html",
        "url_strip_query": True,
        "rank_penalty": 25.0,   # hardware: marca/garantia UE incertas; retira pontos em best_value
        "use_hint": False,
        "verticals": ["tech", "general"],
    },
    "amazon_es": {
        "search_url": "https://www.amazon.es/s?k={q}",
        "page_url": "https://www.amazon.es/s?k={q}&page={page}",
        "base_url": "https://www.amazon.es",
        "card": "div[data-component-type='s-search-result']",
        "title": "h2",
        "price": "span.a-price > span.a-offscreen",
        "image": "img.s-image",
        "id_attr": "data-asin",
        "url_template": "https://www.amazon.es/dp/{id}",
        "country": "ES",
        "use_hint": False,
        "verticals": ["tech", "general"],
        "solo": True,   # só corre depois das outras lojas (em paralelo devolvia 0 itens)
    },
    "motocard": {
        "search_url": "https://www.motocard.com/pt/search?q={q}&p=1&nidx",
        "page_url": "https://www.motocard.com/pt/search?p={page}&order=relevance&q={q}&nidx",
        "base_url": "https://www.motocard.com",
        "verticals": ["moto"],
        "trust_search": True,
    },
    "standvirtual": {
        "search_url": "https://www.standvirtual.com/carros/q-{q}",
        "page_url": "https://www.standvirtual.com/carros/q-{q}?page={page}",
        "base_url": "https://www.standvirtual.com",
        "q_sep": "-",
        "card": "article[data-id]",
        "title": "h2",
        "price": "h3 span",
        "link": "h2 a",
        "image": "img",
        "id_attr": "data-id",
        "default_condition": "used",
        "wait": "article[data-id] h3 span",
        "extra_domains": ["standvirtual.com"],
        "verticals": ["cars"],
    },
    "mediamarkt": {
        "search_url": "https://www.mediamarkt.es/es/search.html?query={q}",
        "base_url": "https://www.mediamarkt.es",
        "country": "ES",
        "verticals": ["tech", "general"],
    },
    "globaldata": {
        "search_url": "https://www.globaldata.pt/search?q={q}&search-button=&lang=null",
        "base_url": "https://www.globaldata.pt",
        "card": "div.product[data-pid]",
        "title": "a[data-qa='product-tile-name-link']",
        "price": ".js-sales .js-unit-price",
        "link": "a[data-qa='product-tile-name-link']",
        "id_attr": "data-pid",
        "country": "PT",
        "verticals": ["tech"],
    },
        "assismatica": {
        "search_url": "https://www.assismatica.pt/pt/pesquisa?q={q}",
        "page_url": "https://www.assismatica.pt/pt/pesquisa?p={page}&q={qp}",
        "base_url": "https://www.assismatica.pt",
        "card": "li.product-item",
        "title": "h5.product-item__title a",
        "price": ".prodcut-price",
        "link": "h5.product-item__title a",
        "image": "img",
        "id_attr": None,
        "country": "PT",
        "verticals": ["tech"],
    },
    "mhr": {
        "search_url": "https://www.mhr.pt/p4-pesquisa-pt?token=&category=&pesquisa={q}",
        "base_url": "https://www.mhr.pt",
        "card": "div.cat_wrap div.prd_d",
        "title": "div.prd_title a",
        "price": "div.price",
        "link": "div.prd_title a",
        "image": "img",
        "id_attr": "id",
        "country": "PT",
        "verticals": ["tech"],
    },
    "imperiomultimedia": {
        "search_url": "https://imperiomultimedia.pt/?s={q}",
        "base_url": "https://imperiomultimedia.pt",
        "card": "div.e-loop-item.product",
        "title": "h1 a",
        "price": ".preco-atual .woocommerce-Price-amount",
        "link": "h1 a",
        "image": "img",
        "country": "PT",
        "verticals": ["tech"],
    },
}


import json as _json
from backend.config import DATA_DIR as _DATA_DIR


def _load_auto_stores() -> None:
    path = _DATA_DIR / "stores_auto.json"
    if not path.exists():
        return
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for key, cfg in data.items():
        if key not in STORES and isinstance(cfg, dict) and not cfg.get("disabled"):
            STORES[key] = cfg


_load_auto_stores()

# Tipo de loja (não vem do registo automático, que pode ser regenerado).
_STORE_KINDS = {"bertrand": "books", "almedina": "books"}
for _k, _kind in _STORE_KINDS.items():
    if _k in STORES:
        STORES[_k]["kind"] = _kind
