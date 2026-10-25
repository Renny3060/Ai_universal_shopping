"""Verificação de plausibilidade dos itens que uma loja devolveu (funções puras).

Apanha seletores que "funcionam" mas apanham a coisa errada: o mesmo preço em tudo, títulos ou
links repetidos, títulos que são lixo, preços simbólicos ou links para outro domínio.
Não prova que o preço está certo; só rejeita os casos claramente errados.
"""
import statistics
from typing import Optional
from urllib.parse import urlsplit


def _host(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def check_plausibility(items: list, base_url: str, extra_domains: Optional[list[str]] = None,
                       min_items: int = 5) -> tuple[bool, list[str]]:
    """Devolve (plausível, motivos). `items` precisam de .price, .title e .url."""
    n = len(items)
    if n < min_items:
        return False, [f"só {n} itens (mínimo {min_items})"]
    reasons: list[str] = []
    prices = [round(float(i.price), 2) for i in items]
    titles = [i.title.strip().lower() for i in items]
    urls = [i.url for i in items]

    if len(set(prices)) / n < 0.3:
        reasons.append("preços quase todos iguais")
    if len(set(titles)) / n < 0.5:
        reasons.append("títulos repetidos")
    if len(set(urls)) / n < 0.8:
        reasons.append("links repetidos")
    if sum(1 for t in titles if len(t) < 8) / n > 0.2:
        reasons.append("títulos demasiado curtos")
    if sum(1 for p in prices if p < 1.0) / n > 0.2:
        reasons.append("muitos preços abaixo de 1 €")
    if statistics.median(prices) > 100_000:
        reasons.append("preço mediano absurdo")

    allowed = {_host(base_url)} | {d.lower().removeprefix("www.") for d in (extra_domains or [])}
    inside = sum(1 for u in urls if any(_host(u) == a or _host(u).endswith("." + a) for a in allowed if a))
    if inside / n < 0.8:
        reasons.append("links para outro domínio")
    return not reasons, reasons
