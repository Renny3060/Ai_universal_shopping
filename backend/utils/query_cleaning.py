import re
from typing import Optional

# Remove expressões de orçamento: "até 500€", "máx 1500 euros", "por menos de 300", "500€"
_BUDGET = [
    r"\b(até|ate|máximo|maximo|máx|max|por menos de|menos de|abaixo de|no máximo)\.?\s*(de\s+)?"
    r"\d[\d\s.,]*\s*(€|eur(os)?)?",
    r"\d[\d\s.,]*\s*(€|eur(os)?)\b",
]

# Número com milhares ("1.500", "1 500") e/ou decimais ("900,50") ou simples ("650")
_NUM = r"(?<![\d.,])(\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
_KEYWORD = (
    r"\b(?:até|ate|máximo|maximo|máx|max|por menos de|menos de|abaixo de|no máximo)\.?\s*(?:de\s+)?"
    + _NUM + r"\s*(?:€|eur(?:os)?\b)?"
)
# Sem moeda-só com espaços de milhares: "RTX 570 900€" seria lido como 570 900
_CURRENCY_ONLY = r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(?:€|eur(?:os)?\b)"


def _to_float(raw: str) -> Optional[float]:
    s = raw.replace("\u00a0", " ").strip()
    if "," in s:                                  # vírgula = decimal; pontos/espaços = milhares
        s = s.replace(".", "").replace(" ", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:[.\s]\d{3})+", s):
        s = s.replace(".", "").replace(" ", "")   # só milhares
    try:
        return float(s)
    except ValueError:
        return None


def extract_budget(text: str) -> Optional[float]:
    """Orçamento máximo escrito no pedido ("até 900€", "máx 1.500 euros", "500€"), ou None.
    Fallback para quando o LLM (Parser) não está disponível."""
    m = re.search(_KEYWORD, text, flags=re.IGNORECASE) or re.search(_CURRENCY_ONLY, text, flags=re.IGNORECASE)
    if not m:
        return None
    value = _to_float(m.group(1))
    return value if value and value > 0 else None


def clean_search_term(text: str) -> str:
    """Tira do texto o orçamento e a pontuação solta, deixando só o que se pesquisa na loja."""
    t = text
    for pattern in _BUDGET:
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)
    t = re.sub(r"[,;:]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()