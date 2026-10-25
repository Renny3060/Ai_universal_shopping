import re
from typing import Literal, Optional

from pydantic import BaseModel

from backend.schemas.search import Requirement

# Nomes que o LLM pode dar ao mesmo atributo
ALIASES = {
    "ram_gb": {"ram_gb", "ram", "memory_gb", "memoria_gb", "memoria_ram_gb"},
    "storage_gb": {"storage_gb", "storage", "ssd_gb", "ssd", "disk_gb", "disco_gb"},
    "vram_gb": {"vram_gb", "vram", "gpu_memory_gb", "gpu_vram_gb"},
    "screen_inches": {"screen_inches", "screen_size", "screen_size_inches", "display_inches", "screen"},
}
_KIND_OF_ATTR = {"ram_gb": "ram", "storage_gb": "storage", "vram_gb": "vram"}

# número + unidade (ex.: 16GB, 1TB, 16 Go) ou etiqueta (ex.: RAM, SSD, GDDR7)
_TOKEN = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>gb|tb|go)\b"
    r"|\b(?P<label>gddr\d?x?|gdd|vram|lpddr\d?x?|ddr\d?|so-?dimm|ram|mem[óo]ria|ssd|nvme|hdd|disco|emmc)\b"
)

# polegadas: 15.6" | 27 polegadas | 24 inch (o número não pode fazer parte de outro, ex.: 5060 ")
_SCREEN = re.compile(
    r"(?<![\d.,])(\d{2}(?:[.,]\d)?)\s*(?:\"|”|″|''|pol(?:egadas)?\b|inch(?:es)?\b)"
)


class NumericCheck(BaseModel):
    status: Literal["ok", "fail", "unknown"]
    attribute: str
    operator: str
    wanted: float
    found: Optional[float] = None


def canonical_attribute(name: str) -> Optional[str]:
    n = name.strip().lower()
    for canonical, names in ALIASES.items():
        if n in names:
            return canonical
    return None


def _label_kind(label: str) -> str:
    if label.startswith(("gdd", "vram")):
        return "vram"
    if label in ("ssd", "nvme", "hdd", "disco", "emmc"):
        return "storage"
    return "ram"


def _size_values(title: str) -> list[tuple[str, float]]:
    """Pares (tipo, valor em GB). Cada número liga-se à etiqueta vizinha:
    'N etiqueta' se o título começar por um número, 'etiqueta N' se começar por uma etiqueta."""
    tokens = []
    for m in _TOKEN.finditer(title.lower()):
        if m.group("num"):
            val = float(m.group("num").replace(",", "."))
            if m.group("unit") == "tb":
                val *= 1000
            tokens.append(("num", val, m.group("unit")))
        else:
            tokens.append(("label", _label_kind(m.group("label")), None))
    if not tokens:
        return []

    number_first = tokens[0][0] == "num"
    out: list[tuple[str, float]] = []
    for i, (typ, val, unit) in enumerate(tokens):
        if typ != "num":
            continue
        kind = None
        neighbours = tokens[i + 1:] if number_first else reversed(tokens[:i])
        for typ2, kind2, _ in neighbours:
            if typ2 == "label":
                kind = kind2
            break                      # só o vizinho imediato conta
        if kind is None and unit == "tb":
            kind = "storage"           # TB sem etiqueta: armazenamento
        if kind:
            out.append((kind, val))
    return out


def extract_spec(title: str, attribute: str) -> Optional[float]:
    """Valor do atributo no título, ou None se não existir ou for ambíguo."""
    if attribute == "screen_inches":
        values = {
            float(m.group(1).replace(",", "."))
            for m in _SCREEN.finditer(title.lower())
            if 10 <= float(m.group(1).replace(",", ".")) <= 100
        }
    else:
        kind = _KIND_OF_ATTR[attribute]
        values = {v for k, v in _size_values(title) if k == kind}
    return values.pop() if len(values) == 1 else None


def _parse_requirement(req: Requirement) -> Optional[tuple[str, float]]:
    """(atributo canónico, valor pedido) se o requisito for numérico e suportado."""
    attr = canonical_attribute(req.attribute)
    if not attr or req.operator not in (">=", "<=", "=="):
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", req.value)
    if not m:
        return None
    wanted = float(m.group(0).replace(",", "."))
    if attr == "storage_gb" and "tb" in f"{req.unit or ''} {req.value}".lower():
        wanted *= 1000
    return attr, wanted


def is_numeric_requirement(req: Requirement) -> bool:
    return _parse_requirement(req) is not None


def check_numeric(title: str, req: Requirement) -> Optional[NumericCheck]:
    """None se o requisito não é numérico ou não é suportado."""
    parsed = _parse_requirement(req)
    if parsed is None:
        return None
    attr, wanted = parsed
    found = extract_spec(title, attr)

    if found is None:
        status = "unknown"
    elif req.operator == ">=":
        status = "ok" if found >= wanted else "fail"
    elif req.operator == "<=":
        status = "ok" if found <= wanted else "fail"
    else:
        tol = 0.7 if attr == "screen_inches" else 0.05   # 15" aceita 15.6", 27" aceita 27.0"
        status = "ok" if abs(found - wanted) <= tol else "fail"

    return NumericCheck(status=status, attribute=attr, operator=req.operator,
                        wanted=wanted, found=found)