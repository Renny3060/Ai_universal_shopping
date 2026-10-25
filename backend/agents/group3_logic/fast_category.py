"""Classificação rápida e conservadora por palavras ANTES de chamar o LLM.

Só devolve uma categoria quando o título começa por uma palavra que identifica o artigo sem
ambiguidade (ex.: "Portátil HP 15...", "Memória RAM Kingston...", "SSD Kingston..."). Tudo o que
for ambíguo devolve None e segue para o LLM. Medido contra a classificação do LLM guardada na BD
(scripts/bench_fast_category.py)."""
import re
import unicodedata
from typing import Optional

# Palavras que, em qualquer ponto do título, mostram que é um acessório e não o artigo principal.
_ACCESSORY = re.compile(
    r"\b(?:mala|mochila|bolsa|capa|bolsas|carregador|bateria|suporte|base|cooler|adaptador|caixa|"
    r"ecr[ãa]|teclado|rato|cabo|pel[ií]cula|protetor|dock|hub|fonte|ventoinha|cart[ãa]o|case|"
    r"enclosure|gabinete|skin|pasta)\b"
)

# (categoria, regex sobre o INÍCIO do título, já sem acentos e em minúsculas)
_LEAD_RULES: list[tuple[str, re.Pattern]] = [
    ("laptop", re.compile(r"^(?:novo\s+|recondicionado\s+)?(?:portatil|laptop|notebook|macbook)\b")),
    ("desktop_pc", re.compile(r"^(?:novo\s+)?(?:pc\s+(?:gaming|gamer|desktop|de\s+secretaria)|"
                              r"computador\s+de\s+secretaria|torre\s+(?:gaming|pc|gamer)|desktop\s+pc)\b")),
    ("ram", re.compile(r"^(?:kit\s+)?(?:memoria(?:s)?\s+(?:ram|ddr\d)|ram\s+ddr\d|ddr\d\s+ram)\b")),
    ("ssd", re.compile(r"^(?:disco\s+)?(?:ssd|unidade\s+(?:ssd|de\s+estado\s+solido))\b")),
    ("graphics_card", re.compile(r"^(?:placa\s+grafica|placa\s+de\s+video|gpu)\b")),
    ("cpu", re.compile(r"^processador\b")),
    ("motherboard", re.compile(r"^(?:placa[- ]mae|motherboard)\b")),
    ("psu", re.compile(r"^fonte\s+de\s+alimentacao\b")),
    ("monitor", re.compile(r"^monitor\b")),
]

# Computadores de secretária vendidos com a palavra "portátil" no título (erro comum).
_DESKTOP_HINT = re.compile(r"\b(?:sff|thinkcentre|elitedesk|prodesk|optiplex|tiny|mini\s*pc|all[- ]in[- ]one)\b")
_PSU_ACCESSORY = re.compile(r"\b(?:carregador|laptop|portatil|notebook|adaptador|ac|dc)\b")

# Categorias em que a presença de palavras de acessório no título anula a regra rápida.
_ACCESSORY_SENSITIVE = {"laptop", "desktop_pc"}


def _norm(title: str) -> str:
    t = unicodedata.normalize("NFKD", title.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def fast_classify(title: str) -> Optional[str]:
    t = _norm(title)
    for cat, pat in _LEAD_RULES:
        if pat.search(t):
            if cat in _ACCESSORY_SENSITIVE and _ACCESSORY.search(t):
                return None
            if cat == "laptop" and _DESKTOP_HINT.search(t):
                return None
            if cat == "psu" and _PSU_ACCESSORY.search(t):
                return None
            return cat
    return None
