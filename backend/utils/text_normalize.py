import re
import unicodedata

# Letras cirílicas que se parecem com letras latinas (usadas em títulos para enganar filtros).
_HOMOGLYPHS = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "І": "I", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "а": "a", "е": "e", "і": "i", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
})


def normalize_title(text: str) -> str:
    """NFKC, homóglifos cirílicos para latino e espaços colapsados. Mantém acentos portugueses."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).translate(_HOMOGLYPHS)
    return re.sub(r"\s+", " ", t).strip()