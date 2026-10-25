"""Descoberta automática de lojas: funções puras (sem browser), testáveis.

O browser (Playwright) fica em scripts/discover_store.py; aqui só se interpreta o resultado.
"""
import re
from collections import Counter
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

_TRACKING = {"gclid", "srsltid", "gad_source", "gad_campaignid", "gbraid", "wbraid", "fbclid", "msclkid"}

_PRICE_RE = re.compile(r"\d{1,3}(?:[.\s\u00a0]\d{3})*(?:[.,]\d{1,2})?\s*€|€\s*\d")


def clean_tracking(url: str) -> str:
    """Remove parâmetros de tracking (utm_*, gclid, srsltid...) e o fragmento."""
    parts = urlsplit(url)
    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in _TRACKING and not k.lower().startswith("utm_")
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))


def template_from_url(url: str, term: str) -> Optional[tuple[str, Optional[str]]]:
    """Troca o termo pesquisado no URL por {q}.

    Devolve (template, q_sep) ou None. q_sep é None quando o termo vai com '+' ou '%20'
    (quote_plus, o comportamento por defeito) e '-' ou '_' quando o termo é um slug no caminho.
    """
    words = [w for w in term.strip().split() if w]
    if not words:
        return None
    url = clean_tracking(url)
    if "{" in url or "}" in url:
        return None
    variants = [
        ("+".join(words), None),
        ("%20".join(words), None),
        ("-".join(words), "-"),
        ("_".join(words), "_"),
    ]
    for text, sep in variants:
        pattern = re.compile(re.escape(text), re.I)
        if pattern.search(url):
            return pattern.sub("{q}", url, count=1), sep
    return None


def _sig(el) -> str:
    for attr in ("data-testid", "data-component-type", "data-cy"):
        if el.get(attr) is not None:
            return f"{el.name}[{attr}='{el.get(attr)}']"
    classes = [c for c in (el.get("class") or []) if len(c) < 25 and not re.search(r"\d{3,}", c)][:3]
    return el.name + ("." + ".".join(classes) if classes else "")


def price_card_candidates(html: str, top: int = 6) -> list[tuple[str, int]]:
    """Candidatos a 'cartão de produto': ancestrais que se repetem em volta de elementos com preço.

    Aceita preços sem cêntimos ('450 €'). Devolve [(assinatura, repetições)].
    """
    soup = BeautifulSoup(html, "lxml")
    price_els = [
        e for e in soup.find_all(True)
        if e.name not in ("script", "style", "noscript")
        and (txt := e.get_text(" ", strip=True))
        and len(txt) <= 40 and _PRICE_RE.search(txt)
        and not any(_PRICE_RE.search(c.get_text(" ", strip=True) or "") for c in e.find_all(True))
    ]
    anc: Counter = Counter()
    for e in price_els:
        for p in list(e.parents)[:7]:
            if p.name in ("body", "html", "[document]"):
                break
            anc[_sig(p)] += 1
    ranked = [(s, n) for s, n in anc.most_common() if n >= 3]
    return ranked[:top]


def store_entry(name: str, url: str, template: str, q_sep: Optional[str]) -> str:
    """Texto pronto a colar em STORES (loja lida por JSON-LD, sem 'card')."""
    parts = urlsplit(url)
    lines = [
        f'    "{name}": {{',
        f'        "search_url": "{template}",',
        f'        "base_url": "{parts.scheme}://{parts.netloc}",',
    ]
    if q_sep:
        lines.append(f'        "q_sep": "{q_sep}",')
    lines.append("    },")
    return "\n".join(lines)