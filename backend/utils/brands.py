"""Marcas conhecidas e linhas de produto inequívocas (ex.: ROG -> Asus, MacBook -> Apple).

Usado para: (1) perceber "da Asus ou Lenovo" num pedido; (2) saber de que marca é um título.
Só entram aliases que não são palavras comuns (nada de "yoga", "thin", "katana", "mini").
Fabricantes de chips (Intel, AMD, Nvidia) ficam de fora de propósito: não são a marca do artigo.
"""
import re
import unicodedata

BRANDS: dict[str, tuple[str, ...]] = {
    # computadores e periféricos
    "asus": ("asus", "rog", "tuf gaming", "zenbook", "vivobook", "proart"),
    "acer": ("acer", "predator", "aspire", "travelmate"),
    "lenovo": ("lenovo", "thinkpad", "ideapad", "legion", "loq", "thinkbook"),
    "hp": ("hp", "omen", "victus", "elitebook", "probook"),
    "dell": ("dell", "alienware", "inspiron", "latitude", "xps", "vostro"),
    "msi": ("msi",),
    "apple": ("apple", "macbook", "iphone", "ipad", "imac"),
    "samsung": ("samsung", "galaxy"),
    "lg": ("lg", "ultragear"),
    "gigabyte": ("gigabyte", "aorus"),
    "asrock": ("asrock",),
    "zotac": ("zotac",),
    "palit": ("palit",),
    "gainward": ("gainward",),
    "sapphire": ("sapphire",),
    "xfx": ("xfx",),
    "powercolor": ("powercolor",),
    "pny": ("pny",),
    "inno3d": ("inno3d",),
    "corsair": ("corsair",),
    "kingston": ("kingston", "hyperx"),
    "crucial": ("crucial",),
    "western digital": ("western digital", "wd"),
    "seagate": ("seagate",),
    "sandisk": ("sandisk",),
    "logitech": ("logitech",),
    "razer": ("razer",),
    "steelseries": ("steelseries",),
    "sony": ("sony",),
    "xiaomi": ("xiaomi", "redmi", "poco"),
    "huawei": ("huawei",),
    "oppo": ("oppo",),
    "oneplus": ("oneplus",),
    "motorola": ("motorola",),
    "philips": ("philips",),
    "benq": ("benq",),
    "aoc": ("aoc",),
    "viewsonic": ("viewsonic",),
    "tp-link": ("tp-link", "tplink"),
    "bosch": ("bosch",),
    "makita": ("makita",),
    "dewalt": ("dewalt",),
    # motos e equipamento
    "nolan": ("nolan",),
    "shoei": ("shoei",),
    "arai": ("arai",),
    "agv": ("agv",),
    "hjc": ("hjc",),
    "givi": ("givi",),
    "shad": ("shad",),
    "scorpion": ("scorpion",),
    "schuberth": ("schuberth",),
    "ls2": ("ls2",),
    "airoh": ("airoh",),
    "nexx": ("nexx",),
    "caberg": ("caberg",),
    "sena": ("sena",),
    "alpinestars": ("alpinestars",),
    "dainese": ("dainese",),
    "revit": ("revit", "rev'it"),
    "ixon": ("ixon",),
    "yamaha": ("yamaha",),
    "suzuki": ("suzuki",),
    "kawasaki": ("kawasaki",),
    "ducati": ("ducati",),
    "ktm": ("ktm",),
    "triumph": ("triumph",),
    "harley-davidson": ("harley-davidson", "harley davidson"),
    # automóveis
    "audi": ("audi",),
    "bmw": ("bmw",),
    "volkswagen": ("volkswagen", "vw"),
    "mercedes": ("mercedes", "mercedes-benz"),
    "seat": ("seat", "cupra"),
    "renault": ("renault",),
    "peugeot": ("peugeot",),
    "citroen": ("citroen", "citroën"),
    "opel": ("opel",),
    "ford": ("ford",),
    "toyota": ("toyota",),
    "honda": ("honda",),
    "nissan": ("nissan",),
    "fiat": ("fiat",),
    "skoda": ("skoda", "škoda"),
    "volvo": ("volvo",),
    "mazda": ("mazda",),
    "kia": ("kia",),
    "hyundai": ("hyundai",),
    "tesla": ("tesla",),
}


def fold(text: str) -> str:
    """Minúsculas e sem acentos."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _alias_pattern(alias: str) -> str:
    return re.escape(fold(alias)).replace(r"\ ", r"\s+")


_PATTERNS = {
    brand: re.compile(r"(?<![a-z0-9])(?:" + "|".join(_alias_pattern(a) for a in aliases) + r")(?![a-z0-9])")
    for brand, aliases in BRANDS.items()
}


def find_brands(text: str) -> list[str]:
    """Marcas presentes no texto, pela ordem em que aparecem."""
    t = fold(text)
    found: list[tuple[int, str]] = []
    for brand, pat in _PATTERNS.items():
        m = pat.search(t)
        if m:
            found.append((m.start(), brand))
    return [b for _, b in sorted(found)]


def brand_spans(text: str) -> list[tuple[int, int]]:
    """Posições (no texto sem acentos, que tem o mesmo tamanho que o original em minúsculas
    para letras latinas) de todas as menções a marcas."""
    t = fold(text)
    spans: list[tuple[int, int]] = []
    for pat in _PATTERNS.values():
        spans.extend((m.start(), m.end()) for m in pat.finditer(t))
    return sorted(spans)
