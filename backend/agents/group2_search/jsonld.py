import json
from typing import Any, Iterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from backend.utils.parsing import parse_price

JSONLD_SELECTOR = 'script[type="application/ld+json"]'


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _types(node: dict) -> set[str]:
    return {str(t) for t in _as_list(node.get("@type"))}


def _walk(node: Any) -> Iterator[dict]:
    """Percorre o JSON-LD (listas, @graph, ItemList/ListItem) e devolve nós Product."""
    if isinstance(node, list):
        for n in node:
            yield from _walk(n)
        return
    if not isinstance(node, dict):
        return
    kinds = _types(node)
    if "Product" in kinds:
        yield node
    for key in ("@graph", "itemListElement", "item", "mainEntity"):
        if key in node:
            yield from _walk(node[key])


def _price_of(offers: Any) -> tuple[Optional[float], Optional[str], bool]:
    """(preço, moeda, em stock) da primeira oferta com preço único. AggregateOffer é ignorada."""
    for offer in _as_list(offers):
        if not isinstance(offer, dict) or "AggregateOffer" in _types(offer):
            continue
        raw = offer.get("price")
        if raw is None:
            continue
        price = float(raw) if isinstance(raw, (int, float)) else parse_price(str(raw))
        if not price or price <= 0:
            continue
        availability = str(offer.get("availability", "")).lower()
        in_stock = not any(w in availability for w in ("outofstock", "soldout", "discontinued"))
        return price, offer.get("priceCurrency"), in_stock
    return None, None, True


def extract_products(html: str, base_url: str = "") -> list[dict]:
    """Produtos com nome, URL e preço único no JSON-LD da página (schema.org).
    Funciona em muitas lojas sem seletores CSS. Devolve [] se a loja não o publicar."""
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []
    seen: set[str] = set()
    for block in soup.select(JSONLD_SELECTOR):
        try:
            data = json.loads(block.string or block.get_text() or "")
        except (ValueError, TypeError):
            continue
        for prod in _walk(data):
            name = str(prod.get("name") or "").strip()
            url = prod.get("url")
            if isinstance(url, list):
                url = url[0] if url else None
            price, currency, in_stock = _price_of(prod.get("offers"))
            if not (name and url and price):
                continue
            full_url = urljoin(base_url, str(url))
            if full_url in seen:
                continue
            seen.add(full_url)
            image = prod.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")
            out.append({
                "title": name,
                "url": full_url,
                "price": price,
                "currency": currency or "EUR",
                "image": urljoin(base_url, str(image)) if image else None,
                "external_id": str(prod.get("sku") or prod.get("productID") or ""),
                "in_stock": in_stock,
            })
    return out