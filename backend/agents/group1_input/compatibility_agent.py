import re
from typing import Optional

from pydantic import BaseModel, Field

from backend.schemas.search import Requirement

# ---------- Tabelas de regras ----------
CPU_SOCKET_RULES = [
    (r"ryzen\s*[3579]\s*[3-5]\d{3}", "AM4"),
    (r"ryzen\s*[3579]\s*[789]\d{3}", "AM5"),
    (r"i[3579][- ]?1[01]\d{3}", "LGA1200"),
    (r"i[3579][- ]?1[234]\d{3}", "LGA1700"),
    (r"core\s*ultra\s*[3579]\s*2\d{2}", "LGA1851"),
]

BOARD_SOCKET_RULES = [
    (r"\b(a320|b350|x370|b450|x470|b550|a520|x570)\b", "AM4"),
    (r"\b(a620|b650|x670|b840|b850|x870)\b", "AM5"),
    (r"\b(h410|b460|h470|z490|h510|b560|h570|z590)\b", "LGA1200"),
    (r"\b(h610|b660|h670|z690|b760|h770|z790)\b", "LGA1700"),
    (r"\b(h810|b860|z890)\b", "LGA1851"),
]

SOCKET_RAM = {
    "AM4": {"DDR4"},
    "AM5": {"DDR5"},
    "LGA1200": {"DDR4"},
    "LGA1700": {"DDR4", "DDR5"},
    "LGA1851": {"DDR5"},
}

# Ordem importa: modelos mais específicos primeiro (ex.: '4070 ti' antes de '4070')
GPU_MIN_PSU = [
    ("5090", 1000), ("5080", 850), ("5070 ti", 750), ("5070", 650),
    ("5060 ti", 600), ("5060", 550),
    ("4090", 850), ("4080", 750), ("4070 ti", 700), ("4070", 650),
    ("4060 ti", 550), ("4060", 550),
    ("3090", 850), ("3080", 750), ("3070", 650), ("3060 ti", 600),
    ("3060", 550), ("3050", 450),
    ("rx 7900", 800), ("rx 7800", 700), ("rx 7700", 650), ("rx 7600", 550),
    ("rx 6800", 650), ("rx 6700", 650), ("rx 6600", 500),
]


class CompatibilityReport(BaseModel):
    ok: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------- Deteção ----------
def _first_match(rules, text: str) -> Optional[str]:
    t = text.lower()
    for pattern, value in rules:
        if re.search(pattern, t):
            return value
    return None


def detect_cpu_socket(cpu: str) -> Optional[str]:
    return _first_match(CPU_SOCKET_RULES, cpu)


def detect_board_socket(board: str) -> Optional[str]:
    t = board.lower()
    for sock in ("am4", "am5", "lga1200", "lga1700", "lga1851"):
        if sock in t.replace(" ", ""):
            return sock.upper()
    return _first_match(BOARD_SOCKET_RULES, board)


def detect_ram_type(text: str) -> Optional[str]:
    m = re.search(r"ddr[45]", text.lower())
    return m.group(0).upper() if m else None


def gpu_min_psu(gpu: str) -> Optional[int]:
    t = gpu.lower()
    for key, watts in GPU_MIN_PSU:
        if key in t:
            return watts
    return None


# ---------- Verificação de uma configuração concreta ----------
def check_compatibility(parts: dict) -> CompatibilityReport:
    """parts: chaves opcionais cpu, motherboard, ram, gpu (texto) e psu_watts (int)."""
    issues, warnings = [], []

    cpu_sock = detect_cpu_socket(parts["cpu"]) if parts.get("cpu") else None
    board_sock = detect_board_socket(parts["motherboard"]) if parts.get("motherboard") else None
    ram_type = detect_ram_type(parts["ram"]) if parts.get("ram") else None

    if cpu_sock and board_sock and cpu_sock != board_sock:
        issues.append(f"CPU ({cpu_sock}) incompatível com a placa-mãe ({board_sock}).")

    socket = board_sock or cpu_sock
    if socket and ram_type and ram_type not in SOCKET_RAM.get(socket, set()):
        issues.append(f"Memória {ram_type} não suportada em {socket}.")

    if parts.get("gpu") and parts.get("psu_watts"):
        needed = gpu_min_psu(parts["gpu"])
        if needed and parts["psu_watts"] < needed:
            issues.append(
                f"Fonte de {parts['psu_watts']}W abaixo do recomendado ({needed}W) para esta GPU."
            )

    if not cpu_sock and parts.get("cpu"):
        warnings.append("Não consegui identificar o socket do CPU.")

    return CompatibilityReport(ok=not issues, issues=issues, warnings=warnings)


# ---------- Restrições derivadas do pedido ----------
def derive_constraints(text: str) -> list[Requirement]:
    """A partir do que o utilizador pediu, deduz requisitos que as peças têm de cumprir."""
    out: list[Requirement] = []

    socket = detect_cpu_socket(text)
    if socket:
        out.append(Requirement(attribute="cpu_socket", operator="==", value=socket))
        rams = SOCKET_RAM[socket]
        if len(rams) == 1:
            out.append(Requirement(attribute="ram_type", operator="==", value=next(iter(rams))))

    watts = gpu_min_psu(text)
    if watts:
        out.append(Requirement(attribute="psu_watts", operator=">=", value=str(watts), unit="W"))

    return out