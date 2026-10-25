import re
from typing import Optional


def parse_price(text: str) -> Optional[float]:
    """'1 299,99 €' -> 1299.99 | '1.299,00€' -> 1299.0 | '€1,299.50' -> 1299.5"""
    if not text:
        return None
    m = re.search(r"\d[\d\s\u00a0.,]*", text)
    if not m:
        return None
    s = m.group(0).strip().replace("\u00a0", "").replace(" ", "")
    s = s.rstrip(".,")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):          # 1.299,99
            s = s.replace(".", "").replace(",", ".")
        else:                                     # 1,299.99
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) in (1, 2) else s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 1 and len(parts[-1]) == 3:  # 1.299 -> milhares
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None