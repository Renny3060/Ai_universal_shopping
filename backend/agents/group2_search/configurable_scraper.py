import hashlib
from typing import Optional
from urllib.parse import urljoin
import re
import unicodedata

from bs4 import BeautifulSoup

from backend.agents.group2_search.base_scraper import BaseScraper
from backend.schemas.product import ProductResult
from backend.utils.parsing import parse_price
from backend.agents.group2_search.jsonld import JSONLD_SELECTOR, extract_products
from backend.utils.text_normalize import normalize_title

class ConfigurableScraper(BaseScraper):
    """Agente 8 (Lojas Locais): scraper genérico controlado por seletores CSS.

    Chaves opcionais na configuração da loja:
      title_attr / price_attr / id_attr: lê o valor de um atributo do próprio cartão
      wait: seletor a esperar antes de copiar a página (por defeito, o do preço)
      page_url: modelo do URL das páginas 2, 3... com {q} e {page}
                (ex.: "https://loja.pt/search?query={q}&page={page}")
      seller_label: texto que antecede o vendedor no cartão (ex.: "Vendido por")
    """

    def __init__(self, store: str, config: dict):
        self.store = store
        self.cfg = config
         # Sem "card" na configuração, a loja é lida pelo JSON-LD (schema.org) da página.
        self.wait_selector = (
            config.get("wait") or config.get("price")
            or (JSONLD_SELECTOR if not config.get("card") else None)
        )

    def _q(self, keywords: str) -> str:
        """Termo no URL: por defeito quote_plus; com q_sep (ex.: '-') faz slug sem acentos."""
        sep = self.cfg.get("q_sep")
        if not sep:
            return self.encode(keywords)
        t = unicodedata.normalize("NFKD", keywords.lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", sep, t).strip(sep)

    def build_url(self, keywords: str) -> str:
        return self.cfg["search_url"].format(q=self._q(keywords), qp=self.encode(keywords))

    def build_page_url(self, keywords: str, page: int) -> Optional[str]:
        template = self.cfg.get("page_url")
        if not template:
            return None
        return template.format(q=self._q(keywords), qp=self.encode(keywords), page=page)

    def _condition(self, title: str) -> str:
        """Estado pelo título; se a loja define default_condition (ex.: 'used'), vale quando o título não diz nada."""
        detected = self._detect_condition(title)
        default = self.cfg.get("default_condition")
        return default if default and detected == "new" else detected

    def _text(self, node, selector: Optional[str]) -> str:
        if not selector:
            return ""
        el = node.select_one(selector)
        return el.get_text(" ", strip=True) if el else ""

    @staticmethod
    def _detect_condition(title: str) -> str:
        t = title.lower()
        if "recondicionad" in t or "reacondicionad" in t or "refurbished" in t or "renewed" in t:
            return "refurbished"
        # Outlet / caixa aberta / grade B: artigo já aberto ou devolvido, conta como recondicionado.
        if re.search(r"\boutlet\b|caixa\s+aberta|open[- ]box|\bgrade\s*[abc]\b", t):
            return "refurbished"
        if "usado" in t or "used" in t:
            return "used"
        return "new"

    def _title(self, card) -> str:
        attr = self.cfg.get("title_attr")
        if attr and card.get(attr):
            return normalize_title(str(card.get(attr)))
        return normalize_title(self._text(card, self.cfg.get("title")))

    def _price(self, card) -> Optional[float]:
        attr = self.cfg.get("price_attr")
        if attr and card.get(attr):
            return parse_price(str(card.get(attr)))
        return parse_price(self._text(card, self.cfg.get("price")))

    def _seller(self, card) -> Optional[str]:
        """Vendedor: o texto que vem a seguir a 'seller_label' no cartão (ex.: 'Vendido por')."""
        label = self.cfg.get("seller_label")
        if not label:
            return None
        target = label.lower().strip().rstrip(":")
        texts = list(card.stripped_strings)
        for i, t in enumerate(texts):
            low = t.lower().strip()
            if low.rstrip(": ") == target:                 # etiqueta e nome em blocos separados
                return texts[i + 1] if i + 1 < len(texts) else None
            if low.startswith(target):                     # tudo no mesmo bloco: 'Vendido por: X'
                rest = t.strip()[len(label.strip().rstrip(":")):].strip(" :")
                if rest:
                    return rest
        return None

    def _parse_jsonld(self, html: str) -> list[ProductResult]:
        base = self.cfg.get("base_url", "")
        out: list[ProductResult] = []
        for p in extract_products(html, base):
            ext_id = p["external_id"] or hashlib.sha1(p["url"].encode()).hexdigest()[:12]
            out.append(ProductResult(
                store=self.store,
                external_id=ext_id,
                title=normalize_title(p["title"]),
                url=p["url"],
                price=p["price"],
                currency=p["currency"] or self.cfg.get("currency", "EUR"),
                image_url=p["image"],
                origin_country=self.cfg.get("country", "PT"),
                condition=self._detect_condition(normalize_title(p["title"])),
                in_stock=p["in_stock"],
            ))
        return out
    
    def parse(self, html: str) -> list[ProductResult]:
        if not self.cfg.get("card"):
            return self._parse_jsonld(html)
        soup = BeautifulSoup(html, "lxml")
        base = self.cfg.get("base_url", "")
        out: list[ProductResult] = []

        for card in soup.select(self.cfg["card"]):
            title = self._title(card)
            price = self._price(card)
            if not (title and price):
                continue

            id_attr = self.cfg.get("id_attr")
            ext_id = card.get(id_attr) if id_attr else None
            template = self.cfg.get("url_template")

            if template and ext_id:                 # URL canónico a partir do ID (ex.: /dp/ASIN)
                url = template.format(id=ext_id)
            else:
                if self.cfg.get("link"):
                    link_el = card.select_one(self.cfg["link"])
                elif card.name == "a" and card.get("href"):
                    link_el = card                  # o próprio cartão é o link
                else:
                    link_el = card.find("a")
                href = link_el.get("href") if link_el else None
                if not href:
                    continue
                url = urljoin(base, href)
                if self.cfg.get("url_strip_query"):  # tira o tracking (?algo_pvid=...)
                    url = url.split("?", 1)[0]

            img_el = card.select_one(self.cfg["image"]) if self.cfg.get("image") else card.find("img")
            image = None
            if img_el:
                image = img_el.get("src") or img_el.get("data-src")
                image = urljoin(base, image) if image else None

            if not ext_id and self.cfg.get("id_regex"):
                m = re.search(self.cfg["id_regex"], url)
                ext_id = m.group(1) if m else None
            if not ext_id:
                ext_id = hashlib.sha1(url.encode()).hexdigest()[:12]

            out.append(ProductResult(
                store=self.store,
                external_id=str(ext_id),
                title=title,
                url=url,
                price=price,
                currency=self.cfg.get("currency", "EUR"),
                image_url=image,
                seller_name=self._seller(card),
                origin_country=self.cfg.get("country", "PT"),
                condition=self._condition(title),
            ))
        return out