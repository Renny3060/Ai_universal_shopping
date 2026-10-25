import re
import unicodedata
from typing import Optional

from backend.schemas.ranking import RankedProduct, RejectedProduct
from backend.agents.group3_logic.categories import infer_wanted_category

# Só para verticais de veículos. Padrões aplicados a títulos sem acentos, em minúsculas.
PART_PATTERNS: dict[str, list[str]] = {
    "cars": [
        r"\bpecas?\b", r"\bpara pecas\b", r"\bturbina\b", r"\bturbocompressor\b",
        r"\bfaro(l|is)\b", r"\bjantes?\b", r"\bpneus?\b", r"\bmotor completo\b",
        r"\bmotor de arranque\b", r"\bcaixa de velocidades\b", r"\bcaixa de direc(c)?ao\b",
        r"\bpara-?choques\b", r"\bcapot\b", r"\bairbags?\b", r"\bradiador\b",
        r"\bamortecedor(es)?\b", r"\bpastilhas?\b", r"\bdiscos de travao\b",
        r"\bvolante\b", r"\bbancos\b", r"\bescape\b", r"\bcentralina\b",
        r"\bkit de\b", r"\btampa\b", r"\bespelho(s)?\b", r"\bretrovisor(es)?\b",
        r"\bveio\b", r"\bgrelha\b", r"\bfrente completa\b", r"\btransmissao\b",
        r"\binjetores?\b", r"\balternador\b", r"\bembraiagem\b", r"\bcambota\b",
        r"\bref:",
        # só no início do título (nome da peça a abrir o anúncio)
        r"^(motor|turbo|frente|traseira|caixa|bomba|compressor|suporte|conjunto|painel|vidro|porta|portas|banco|cinto|cabeca|bagageira)\b",
    ],
    "moto": [
        r"\bpecas?\b", r"\bpara pecas\b", r"\bcarenagens?\b", r"\bescape\b",
        r"\bguiador\b", r"\bpneus?\b", r"\bjantes?\b", r"\bamortecedor(es)?\b",
        r"\bpastilhas?\b", r"\bcentralina\b", r"\bkit de\b", r"\bespelho(s)?\b",
    ],
}

# Preço mínimo por vertical, só em lojas mistas (OLX). Abaixo disto o anúncio é
# quase sempre sinal, entrada, lote ou peça.
MIN_PRICE: dict[str, float] = {"cars": 1000.0, "moto": 20.0, "general": 2.0}


def split_non_vehicles(
    items: list[RankedProduct],
    wanted_text: str,
    vertical: Optional[str],
    stores_cfg: dict,
    min_price: Optional[float] = None,
) -> tuple[list[RankedProduct], list[RejectedProduct]]:
    """Rejeita peças/acessórios e preços abaixo do mínimo, só em lojas com mais de uma vertical."""
    if vertical not in PART_PATTERNS and vertical not in MIN_PRICE:
        return items, []
    floor = min_price if min_price is not None else MIN_PRICE.get(vertical)
    keep: list[RankedProduct] = []
    out: list[RejectedProduct] = []
    for it in items:
        cfg = stores_cfg.get(it.product.store, {})
        mixed = len(cfg.get("verticals", [])) > 1
        if not mixed:
            keep.append(it)
            continue
        word = matched_part_word(it.product.title, wanted_text, vertical)
        if word:
            out.append(RejectedProduct(product=it.product, reason=f"parece peça/acessório ('{word}')"))
        elif floor and it.product.price < floor:
            out.append(RejectedProduct(
                product=it.product,
                reason=f"preço abaixo do mínimo para {vertical} ({floor:.0f} €)",
            ))
        else:
            keep.append(it)
    return keep, out


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def matched_part_word(title: str, wanted_text: str, vertical: Optional[str]) -> Optional[str]:
    """Devolve o padrão que faz o título parecer uma peça, ou None.
    Padrões cujo termo aparece no pedido do utilizador ficam isentos."""
    if vertical not in PART_PATTERNS:
        return None
    t, wanted = _norm(title), _norm(wanted_text)
    for pat in PART_PATTERNS[vertical]:
        m = re.search(pat, t)
        if m and not re.search(pat, wanted):
            return m.group(0)
    return None

MOTO_WORDS = [
    "moto", "mota", "motas", "motos", "scooter", "ducati", "yamaha", "kawasaki", "ktm",
    "vespa", "harley", "triumph", "capacete", "motard", "motociclo",
]
CAR_WORDS = [
    "carro", "carros", "automovel", "automoveis", "volkswagen", "vw", "audi", "bmw",
    "mercedes", "seat", "renault", "peugeot", "citroen", "opel", "ford", "toyota", "fiat",
    "skoda", "nissan", "volvo", "kia", "hyundai", "golf", "passat", "polo", "corsa", "clio",
]


def _has_word(text: str, words: list[str]) -> bool:
    t = _norm(text)
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in words)


def detect_vertical(text: str) -> Optional[str]:
    """tech / moto / cars, ou None (= todas as lojas). Determinístico, sem LLM."""
    if infer_wanted_category(text):
        return "tech"
    if _has_word(text, MOTO_WORDS):
        return "moto"
    if _has_word(text, CAR_WORDS):
        return "cars"
    return None