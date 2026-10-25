"""Propõe seletores CSS (card, title, price, link) a partir do HTML de uma página de resultados.

Funções puras (sem rede nem browser). Heurística:
  1. encontra os elementos-folha que parecem preços (ex.: "179,90 €", "€1098,89");
  2. sobe pelos ancestrais para achar o cartão repetido (não aninhado, com título, link e preço);
  3. escolhe seletores de título, link e preço e mede a cobertura em todos os cartões.
Nada é inventado: cada seletor é testado contra o HTML recebido e vem com a cobertura medida.
"""
import json
import re
import unicodedata
from typing import Optional

from bs4 import BeautifulSoup, Tag

from backend.utils.parsing import parse_price

PRICE_TEXT = re.compile(r"^\s*(?:€|eur\s*)?\s*\d{1,3}(?:[.\s\u00a0]\d{3})*(?:[.,]\d{1,2})?\s*(?:€|eur)?\s*$|"
                        r"^\s*(?:€|eur\s*)?\s*\d+(?:[.,]\d{1,2})?\s*(?:€|eur)?\s*$", re.I)
SKIP_TAGS = {"script", "style", "noscript", "option", "select", "template", "head"}
STATE_CLASS = re.compile(
    r"^(active|clone|cloned|first|last|odd|even|selected|hidden|show|hide|open|visible|"
    r"slick-.*|swiper-.*|owl-.*|lSSlide.*|current|focus|hover|loaded|lazyloaded|js-.*-processed)$", re.I)
OLD_TOKENS = {"old", "strike", "strikethrough", "through", "linethrough", "before", "was", "antigo",
              "riscado", "anterior", "rrp", "pvp", "compare", "original", "regular", "crossed",
              "oldprice", "from", "cut"}
NEW_TOKENS = {"new", "special", "sale", "sales", "final", "current", "atual", "promo", "now",
              "actual", "best"}


def _tokens(cls: str) -> set[str]:
    return {t for t in re.split(r"[-_\s]+", cls.lower()) if t}


class _TokenPattern:
    def __init__(self, tokens: set[str], phrases: tuple[str, ...] = ()):
        self.tokens, self.phrases = tokens, phrases

    def search(self, cls: str) -> bool:
        low = cls.lower()
        return bool(_tokens(cls) & self.tokens) or any(p in low for p in self.phrases)


OLD_PATTERN = _TokenPattern(OLD_TOKENS, ("list-price", "line-through", "price-old", "old-price"))
NEW_PATTERN = _TokenPattern(NEW_TOKENS)

TITLE_CANDIDATES = [
    "h1 a", "h2 a", "h3 a", "h4 a", "h5 a", "h6 a",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "[class*=title] a", "[class*=name] a", "[class*=title]", "[class*=name]",
]
LAYOUT_CLASS = re.compile(
    r"^(col|row|large|medium|small|xs|sm|md|lg|xl|xxl|span|flex|grid|relative|absolute|block|inline|"
    r"container|wrapper|item|box|group|product|card|[a-z]{1,3}\d{1,2}|tw-.*|"
    r"[a-z]+-\d+|[a-z]+-(xs|sm|md|lg|xl))$", re.I)
CARD_WORD = re.compile(r"product|item|card|tile|result|hit|prod|article|offer", re.I)
MIN_CARDS = 5
MIN_COVERAGE = 0.85


def _valid_class(c: str) -> bool:
    if not re.match(r"^[A-Za-z_][\w-]*$", c) or len(c) > 40:
        return False
    if re.search(r"\d{3,}", c) or STATE_CLASS.match(c):
        return False
    return True


def _selector_for(el: Tag) -> str:
    classes = [c for c in (el.get("class") or []) if _valid_class(c)]
    return el.name + "".join("." + c for c in classes)


def _is_price_leaf(el: Tag) -> Optional[float]:
    if el.name in SKIP_TAGS or el.find(True) is not None:
        return None
    if any(p.name in SKIP_TAGS for p in el.parents if isinstance(p, Tag)):
        return None
    text = el.get_text(" ", strip=True)
    if not text or len(text) > 20 or not PRICE_TEXT.match(text):
        return None
    if "€" not in text and "eur" not in text.lower():
        return None
    value = parse_price(text)
    return value if value and value > 0 else None


def _price_leaves(scope) -> list[tuple[Tag, float]]:
    out = []
    for el in scope.find_all(True):
        v = _is_price_leaf(el)
        if v is not None:
            out.append((el, v))
    return out


def _text_of(el: Optional[Tag]) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _nested(cards: list[Tag]) -> bool:
    ids = {id(c) for c in cards}
    for c in cards:
        if any(id(p) in ids for p in c.parents):
            return True
    return False


def _pick_title(cards: list[Tag]) -> Optional[tuple[str, float]]:
    for sel in TITLE_CANDIDATES:
        texts = []
        for c in cards:
            t = _text_of(c.select_one(sel))
            ok = len(t) >= 6 and sum(ch.isalpha() for ch in t) >= 4 and not PRICE_TEXT.match(t)
            texts.append(t if ok else "")
        good = [t for t in texts if t]
        if len(good) / len(cards) >= MIN_COVERAGE and len(set(good)) >= 0.2 * len(good):
            return sel, len(good) / len(cards)
    return None


def _pick_link(cards: list[Tag], title_sel: str) -> Optional[tuple[str, float]]:
    candidates = []
    if title_sel.endswith(" a"):
        candidates.append(title_sel)
    else:
        candidates += [f"a:has({title_sel})", f"{title_sel} a"]
    candidates.append("a[href]")
    for sel in candidates:
        try:
            hrefs = []
            for c in cards:
                a = c.select_one(sel)
                h = a.get("href") if a else None
                hrefs.append(h if h and not h.startswith(("#", "javascript")) else "")
        except Exception:
            continue
        good = [h for h in hrefs if h]
        if len(good) / len(cards) >= MIN_COVERAGE and len(set(good)) >= 0.2 * len(good):
            return sel, len(good) / len(cards)
    return None


def _old_like(el: Tag, card: Tag) -> bool:
    node = el
    for _ in range(4):
        if node is None or node is card:
            break
        cls = " ".join(node.get("class") or [])
        if cls and OLD_PATTERN.search(cls):
            return True
        node = node.parent if isinstance(node.parent, Tag) else None
    return False


def _new_like(el: Tag, card: Tag) -> bool:
    node = el
    for _ in range(4):
        if node is None or node is card:
            break
        cls = " ".join(node.get("class") or [])
        if cls and NEW_PATTERN.search(cls):
            return True
        node = node.parent if isinstance(node.parent, Tag) else None
    return False


def _pick_price(cards: list[Tag]) -> Optional[dict]:
    sels: list[str] = []
    for c in cards[:12]:
        for leaf, _ in _price_leaves(c):
            base = _selector_for(leaf)
            variants = [base]
            for cls in leaf.get("class") or []:
                if _valid_class(cls) and not LAYOUT_CLASS.match(cls):
                    variants.append(f"{leaf.name}.{cls}")
            parent = leaf.parent if isinstance(leaf.parent, Tag) else None
            if parent is not None and parent is not c:
                ps = _selector_for(parent)
                variants.append(f"{ps} {base}")
                grand = parent.parent if isinstance(parent.parent, Tag) else None
                if grand is not None and grand is not c:
                    variants.append(f"{_selector_for(grand)} {ps} {base}")
            for v in variants:
                if v not in sels:
                    sels.append(v)
    best = None
    for sel in sels:
        try:
            picked = [(c, c.select_one(sel)) for c in cards]
        except Exception:
            continue
        valued = [(c, el, parse_price(_text_of(el))) for c, el in picked
                  if el is not None and PRICE_TEXT.match(_text_of(el))]
        valued = [(c, el, v) for c, el, v in valued if v and v > 0]
        cov = len(valued) / len(cards)
        if cov < MIN_COVERAGE:
            continue
        old = sum(1 for c, el, _ in valued if _old_like(el, c)) / len(valued)
        if old > 0.1:
            continue
        new = sum(1 for c, el, _ in valued if _new_like(el, c)) / len(valued)
        # sinal de preço antigo: nos cartões com 2+ preços, o escolhido é quase sempre o maior
        multi = maxed = 0
        for c, el, v in valued:
            vals = {round(x, 2) for _, x in _price_leaves(c)}
            if len(vals) >= 2:
                multi += 1
                maxed += 1 if round(v, 2) == max(vals) else 0
        suspect = multi >= 3 and maxed / multi > 0.9
        price_word = bool(re.search(r"pric|prec|valor|amount|value|cost", sel, re.I))
        score = (0 if suspect else 1, cov >= 0.95, price_word, new, cov, -len(sel))
        if best is None or score > best["score"]:
            best = {"sel": sel, "cov": cov, "suspect": suspect, "score": score}
    return best


def _candidate_selectors(leaves: list[Tag]) -> list[tuple[str, int]]:
    """(seletor, nível) por ancestral: nível 1 = mais perto do preço. Inclui variantes com uma só classe."""
    out: list[tuple[str, int]] = []
    seen: set[str] = set()
    generic = {"div", "span", "li", "ul", "section", "p", "a", "article"}
    for leaf in leaves[:8]:
        node = leaf.parent
        for level in range(1, 10):
            if not isinstance(node, Tag) or node.name in ("body", "html", "[document]"):
                break
            variants = [_selector_for(node)]
            for c in node.get("class") or []:
                if _valid_class(c) and not LAYOUT_CLASS.match(c):
                    variants.append(f"{node.name}.{c}")
            if node.name in ("li", "article") and node.name not in variants:
                variants.append(node.name)
            for sel in variants:
                if sel in seen or (sel in generic and node.name not in ("li", "article")):
                    continue
                seen.add(sel)
                out.append((sel, level))
            node = node.parent
    return out


def propose(html: str) -> Optional[dict]:
    """Devolve {card, title, price, link, n_cards, cov_*, flags, samples} ou None."""
    soup = BeautifulSoup(html, "lxml")
    leaves = _price_leaves(soup)
    if len(leaves) < MIN_CARDS:
        return None
    selectors = _candidate_selectors([el for el, _ in leaves])
    level_of = dict(selectors)
    passing: list[dict] = []
    for sel, _lvl in selectors:
        try:
            cards = [c for c in soup.select(sel) if c.name not in SKIP_TAGS]
        except Exception:
            continue
        if len(cards) < MIN_CARDS or _nested(cards):
            continue
        with_price = [c for c in cards if _price_leaves(c)]
        if len(with_price) / len(cards) < MIN_COVERAGE or len(with_price) > 1.3 * len(leaves):
            continue
        with_price = [c for c in with_price if len({round(v, 2) for _, v in _price_leaves(c)}) <= 3]
        if len(with_price) < MIN_CARDS:
            continue
        title = _pick_title(with_price)
        if not title:
            continue
        link = _pick_link(with_price, title[0])
        if not link:
            continue
        price = _pick_price(with_price)
        if not price:
            continue
        passing.append({
            "card": sel, "title": title[0], "link": link[0], "price": price["sel"],
            "n_cards": len(with_price), "cov_title": title[1], "cov_link": link[1],
            "cov_price": price["cov"], "price_suspect": price["suspect"],
            "_cards": with_price,
        })
    if not passing:
        return None
    # o mais exterior que ainda passa (mantém a imagem e o resto do cartão); empate: mais cartões
    best = max(passing, key=lambda p: (level_of[p["card"]], bool(CARD_WORD.search(p["card"])),
                                       p["n_cards"], -len(p["card"])))
    cards = best.pop("_cards")
    for p in passing:
        p.pop("_cards", None)
    samples = []
    for c in cards[:3]:
        t = _text_of(c.select_one(best["title"]))[:60]
        a = c.select_one(best["link"])
        samples.append((t, _text_of(c.select_one(best["price"])), (a.get("href") if a else "")[:70]))
    best["samples"] = samples
    best["flags"] = []
    if best["price_suspect"]:
        best["flags"].append("preço pode ser o antigo (riscado)")
    if best["n_cards"] < 8:
        best["flags"].append("poucos cartões")
    if min(best["cov_title"], best["cov_link"], best["cov_price"]) < 0.9:
        best["flags"].append("cobertura < 90%")
    return best


def page_hint(html: str) -> Optional[str]:
    """Primeiro href que aponta para a página 2 (só para um humano rever; não é usado sozinho)."""
    m = re.search(r'href="([^"]*[?&/](?:p|page|pagina|pg|pag)[=/]2(?:[&"#/][^"]*)?)"', html, re.I)
    return m.group(1).replace("&amp;", "&") if m else None


def term_in_html(html: str, term: str) -> bool:
    low = html.lower()
    flat = "".join(c for c in unicodedata.normalize("NFKD", term.lower()) if not unicodedata.combining(c))
    return any(v in low for v in {term.lower(), flat, term.lower().replace(" ", "+"),
                                  term.lower().replace(" ", "%20"), term.lower().replace(" ", "-")})


def store_slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


# Países com preços em euros. As lojas geradas assumem EUR (não há taxas de câmbio no sistema),
# por isso as de outras moedas não são geradas: os preços ficariam errados no ranking.
EURO_COUNTRIES = {"PT", "ES", "DE", "FR", "IT", "NL", "BE", "AT", "FI", "IE", "LU", "GR", "SK",
                  "SI", "EE", "LV", "LT", "HR", "MT", "CY"}


def is_euro_country(code: str) -> bool:
    return (code or "").strip().upper() in EURO_COUNTRIES


def vertical_for(category_key: str) -> list[str]:
    """Hardware e eletrónica -> tech; motos -> moto; o resto -> general.

    'auto' fica em general de propósito: são sobretudo peças e acessórios, que não devem
    aparecer em pesquisas de carros (vertical cars)."""
    return {"hardware": ["tech"], "eletronica": ["tech"], "moto": ["moto"]}.get(category_key, ["general"])


def _py(value) -> str:
    """Valor como literal Python (aspas duplas; True/False e não true/false)."""
    if isinstance(value, bool):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_py(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def entry_text(key: str, cfg: dict) -> str:
    lines = [f'    "{key}": {{']
    for k in ("search_url", "base_url", "card", "title", "price", "link", "q_sep", "country",
              "currency", "verticals", "default_condition", "private_listings"):
        if k in cfg:
            lines.append(f"        {json.dumps(k)}: {_py(cfg[k])},")
    lines.append("    },")
    return "\n".join(lines)


def merge_stores(existing: dict, generated: dict, keys: list[str]) -> tuple[dict, list[str], list[str]]:
    """Junta ao registo as lojas geradas em `keys`. Devolve (registo, adicionadas, ignoradas).

    Nunca substitui uma entrada que já existe no registo; ignora chaves que não estão em `generated`.
    """
    merged = dict(existing)
    added: list[str] = []
    skipped: list[str] = []
    for key in keys:
        if key in merged or key not in generated:
            skipped.append(key)
            continue
        merged[key] = generated[key]
        added.append(key)
    return merged, added, skipped
