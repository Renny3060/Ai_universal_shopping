"""Interpretação determinística (sem LLM, instantânea) de pedidos longos e complexos.

Exemplo:
  "Quero um portátil gaming da Asus ou Lenovo com RTX 4060, 16GB de RAM, SSD 512GB e ecrã de
   15,6 polegadas, novo, entre 800 e 1200€, de preferência preto"
vira: termo "portátil gaming rtx 4060 16gb", orçamento 800 a 1200, estado novo, marcas
asus/lenovo, requisitos (RAM >= 16, SSD >= 512, ecrã 15,6), cor preta como preferência.

O termo de pesquisa na loja leva só o essencial (tipo de artigo, modelo de GPU, a marca se for
uma só); o resto são filtros aplicados depois aos resultados (ver group3_logic/request_filters).
O LLM (Grupo 1) continua a correr em paralelo e só serve de complemento (ver finalize_request).
"""
import re
from typing import Optional

from pydantic import BaseModel, Field

from backend.agents.group3_logic.categories import infer_wanted_category
from backend.agents.group3_logic.spec_check import canonical_attribute, is_numeric_requirement
from backend.schemas.search import ProductSpecs, Requirement
from backend.utils.brands import brand_spans, find_brands
from backend.utils.query_cleaning import _to_float, clean_search_term

MAX_TERM_WORDS = 5   # acima disto o termo é demasiado longo: usa-se o LLM para o resumir

_NUM = r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
_CUR = r"(?:€|eur(?:os)?\b)"

_RANGE = re.compile(rf"\bentre\s+{_NUM}\s*{_CUR}?\s*(?:e|a)\s+{_NUM}\s*{_CUR}?", re.I)
_RANGE2 = re.compile(rf"\bde\s+{_NUM}\s*{_CUR}?\s+a\s+{_NUM}\s*{_CUR}", re.I)
_MIN = re.compile(
    rf"\b(?:a partir de|m[ií]nimo(?:\s+de)?|mais de|acima de|superior a)\s+{_NUM}\s*{_CUR}", re.I)
_MAX_KW = re.compile(
    r"\b(?:até|ate|máximo|maximo|máx|max|por menos de|menos de|abaixo de|no máximo)\.?\s*(?:de\s+)?"
    + _NUM + r"(?!\d)\s*(?:€|eur(?:os)?\b)?(?!\s*(?:gb|go|tb|hz|pol|polegadas|\"|mah))", re.I)
_MAX_CUR = re.compile(r"(?<![\d.,])" + _NUM + r"\s*" + _CUR, re.I)

# ---------- requisitos numéricos ----------
_SZ = r"(\d+(?:[.,]\d+)?)\s*(gb|go|tb)"
_VRAM = re.compile(rf"{_SZ}\s*(?:de\s+)?(?:(vram)|gddr\d?x?)\b", re.I)
_RAM_1 = re.compile(rf"{_SZ}\s*(?:de\s+)?(?:mem[óo]ria\s+)?(ram)\b", re.I)
_RAM_2 = re.compile(rf"\b(ram)\s*(?:de\s+)?{_SZ}", re.I)
_STO_1 = re.compile(
    rf"\b(ssd|nvme|hdd|disco(?:\s+(?:ssd|nvme|duro))?|armazenamento)\s*(?:de\s+)?{_SZ}", re.I)
_STO_2 = re.compile(rf"{_SZ}\s*(?:de\s+)?(ssd|nvme|hdd|disco|armazenamento)\b", re.I)
_SCREEN_1 = re.compile(
    r"(?<![\d.,])(\d{2}(?:[.,]\d)?)\s*(?:\"|”|″|''|polegadas?|pulgadas?|pol\b|inch(?:es)?\b)", re.I)
_SCREEN_2 = re.compile(
    r"\b(?:ecr[ãa]|ecran|tela|display)\s*(?:de\s+)?(\d{2}(?:[.,]\d)?)\b(?!\s*(?:gb|hz|tb))", re.I)
_HZ = re.compile(r"\b(\d{2,3})\s*hz\b", re.I)

# ---------- chips ----------
_GPU = re.compile(
    r"\b(?:nvidia\s+)?(?:geforce\s+|radeon\s+)?(rtx|gtx|rx|arc)\s*(\d{3,4})\s*(ti\s+super|super|ti|xtx|xt)?\b",
    re.I)

# ---------- estado ----------
_NOT_USED = re.compile(
    r"\b(?:sem\s+usados?|n[ãa]o\s+(?:quero\s+)?usados?|nada\s+de\s+usados?|exceto\s+usados?)\b", re.I)
_NEW = re.compile(r"\b(?:novos?|novas?)\b", re.I)
_USED = re.compile(r"\b(?:usad[oa]s?|segunda\s+m[ãa]o)\b", re.I)
_REFURB = re.compile(r"\b(?:recondicionad[oa]s?|reacondicionad[oa]s?|refurbished|renewed)\b", re.I)

# ---------- preferências (não obrigatórias) ----------
_SOFT = re.compile(
    r"\b(?:de\s+prefer[êe]ncia|preferencialmente|se\s+poss[íi]vel|idealmente|se\s+houver|seria\s+bom|"
    r"gostava\s+(?:que|de\s+ter)|nice\s+to\s+have)\b", re.I)

_COLORS = {"preto", "preta", "pretos", "pretas", "branco", "branca", "azul", "vermelho", "vermelha",
           "verde", "cinzento", "cinza", "rosa", "dourado", "dourada", "prateado", "prateada",
           "laranja", "amarelo", "roxo", "black", "white"}

# Onde acaba o "nome do artigo" e começa a descrição.
_HEAD_END = re.compile(r"[,;]|\b(?:com|que|para|sem|equipado|onde|cujo|cuja)\b", re.I)
_FILLERS = {"quero", "queria", "procuro", "preciso", "gostava", "gostaria", "comprar", "encontrar",
            "de", "da", "do", "um", "uma", "uns", "umas", "o", "a", "os", "as", "estou", "à", "procura",
            "ando", "eu", "me", "mim", "algo", "bom", "boa", "e", "ou", "em", "na", "no", "ver"}
_TRAIL_FILLERS = {"de", "da", "do", "e", "ou", "um", "uma", "com", "para", "que", "em"}
# Etiquetas de requisitos que não fazem parte do nome do artigo (a não ser que sejam tudo o que há).
_LABELS = {"ram", "vram", "ssd", "nvme", "hdd", "disco", "armazenamento", "memória", "memoria", "duro"}


class ParsedRequest(BaseModel):
    raw: str
    term: str                                   # termo curto para pesquisar nas lojas
    max_budget: Optional[float] = None
    min_budget: Optional[float] = None
    conditions: list[str] = Field(default_factory=list)       # estados aceites; [] = qualquer
    brands: list[str] = Field(default_factory=list)           # obrigatórias (qualquer uma)
    soft_brands: list[str] = Field(default_factory=list)      # preferidas
    cpu: Optional[str] = None                                  # família: "i7", "ryzen 5", "ultra 7"
    gpu: Optional[str] = None                                  # "rtx 4060", "rx 7600 xt"
    requirements: list[Requirement] = Field(default_factory=list)
    extras: list[str] = Field(default_factory=list)           # cores, 144hz...: só bónus
    nice_to_have: list[str] = Field(default_factory=list)     # texto das preferências
    needs_llm_term: bool = False                               # termo vazio ou demasiado longo


# ---------- chips: também usados para comparar com os títulos ----------
_CPU_PATTERNS = [
    (re.compile(r"core\s*ultra\s*([579])", re.I), "ultra {}"),
    (re.compile(r"\bi([3579])[- ]?\d{3,5}", re.I), "i{}"),
    (re.compile(r"core\s*i([3579])\b", re.I), "i{}"),
    (re.compile(r"(?<![a-z0-9])i([3579])(?![a-z0-9])", re.I), "i{}"),
    (re.compile(r"ryzen\s*(?:ai\s*)?([3579])\b", re.I), "ryzen {}"),
    (re.compile(r"(?:macbook|apple)[^,;]{0,40}?(?<![a-z0-9])m([1-4])(?![a-z0-9])", re.I), "m{}"),
]


def extract_cpu(text: str) -> Optional[str]:
    """Família do processador no texto ("i7", "ryzen 5", "ultra 7", "m2") ou None."""
    for pat, fmt in _CPU_PATTERNS:
        m = pat.search(text)
        if m:
            return fmt.format(m.group(1))
    return None


def _gpu_key(m: re.Match) -> str:
    suffix = re.sub(r"\s+", " ", (m.group(3) or "").lower()).strip()
    return f"{m.group(1).lower()} {m.group(2)}" + (f" {suffix}" if suffix else "")


def _cut(text: str, m: re.Match, keep: str = " ") -> str:
    return text[:m.start()] + keep + text[m.end():]


def _gb(num: str, unit: str) -> float:
    v = float(num.replace(",", "."))
    return v * 1000 if unit.lower() == "tb" else v


def _fmt(v: float) -> str:
    return f"{v:g}"


def _extract_budget(text: str) -> tuple[Optional[float], Optional[float], str]:
    lo = hi = None
    m = _RANGE.search(text) or _RANGE2.search(text)
    if m:
        a, b = _to_float(m.group(1)), _to_float(m.group(2))
        if a and b:
            lo, hi = sorted((a, b))
        return lo, hi, _cut(text, m)
    m = _MIN.search(text)
    if m:
        lo = _to_float(m.group(1))
        text = _cut(text, m)
    m = _MAX_KW.search(text) or _MAX_CUR.search(text)
    if m:
        v = _to_float(m.group(1))
        hi = v if v and v > 0 else None
        text = _cut(text, m)
    return lo, hi, text


def _extract_specs(text: str) -> tuple[list[Requirement], dict[str, str], list[str], str]:
    """Requisitos numéricos. Devolve (requisitos, ficha 'tipo -> token para o termo', extras, texto).
    O nome da etiqueta (ssd, ram...) fica no texto: pode ser tudo o que o pedido diz do artigo."""
    reqs: list[Requirement] = []
    tokens: dict[str, str] = {}
    extras: list[str] = []

    def add(attr: str, op: str, value: float, unit: str) -> None:
        reqs.append(Requirement(attribute=attr, operator=op, value=_fmt(value), unit=unit, mandatory=True))

    def sub_all(pat: re.Pattern, handler) -> None:
        nonlocal text
        while True:
            m = pat.search(text)
            if not m:
                return
            label = handler(m) or " "
            text = text[:m.start()] + f" {label} " + text[m.end():]

    def vram(m):
        add("vram_gb", ">=", _gb(m.group(1), m.group(2)), "GB")
        return None

    def ram(m):
        num, unit = (m.group(1), m.group(2)) if m.re is _RAM_1 else (m.group(2), m.group(3))
        add("ram_gb", ">=", _gb(num, unit), "GB")
        tokens.setdefault("ram", f"{_fmt(float(num.replace(',', '.')))}{unit.lower().replace('go', 'gb')}")
        return "ram_"          # "_" evita que a etiqueta volte a casar com outro requisito

    def sto(m):
        if m.re is _STO_1:
            label, num, unit = m.group(1), m.group(2), m.group(3)
        else:
            num, unit, label = m.group(1), m.group(2), m.group(3)
        add("storage_gb", ">=", _gb(num, unit), "GB")
        tokens.setdefault("storage", f"{_fmt(float(num.replace(',', '.')))}{unit.lower().replace('go', 'gb')}")
        return label.split()[0].lower() + "_"

    def screen(m):
        v = float(m.group(1).replace(",", "."))
        if 10 <= v <= 100:
            add("screen_inches", "==", v, "inch")
            tokens.setdefault("screen", f"{_fmt(v)} polegadas")
        return None

    sub_all(_VRAM, vram)
    sub_all(_RAM_1, ram)
    sub_all(_RAM_2, ram)
    sub_all(_STO_1, sto)
    sub_all(_STO_2, sto)
    sub_all(_SCREEN_1, screen)
    sub_all(_SCREEN_2, screen)
    for m in _HZ.finditer(text):
        extras.append(f"{m.group(1)}hz")
    text = _HZ.sub(" ", text)
    text = re.sub(r"\b(ram|ssd|nvme|hdd|disco|armazenamento)_", r"\1", text)
    return reqs, tokens, extras, text


def _extract_conditions(text: str) -> tuple[list[str], str]:
    excluded: set[str] = set()
    if _NOT_USED.search(text):
        excluded.add("used")
        text = _NOT_USED.sub(" ", text)
    wanted: list[str] = []
    for pat, cond in ((_NEW, "new"), (_REFURB, "refurbished"), (_USED, "used")):
        if pat.search(text):
            wanted.append(cond)
            text = pat.sub(" ", text)
    if wanted:
        return [c for c in wanted if c not in excluded], text
    if excluded:
        return [c for c in ("new", "refurbished") if c not in excluded], text
    return [], text


def _strip_words(words: list[str]) -> list[str]:
    while words and words[0] in _FILLERS:
        words = words[1:]
    while words and words[-1] in _TRAIL_FILLERS:
        words = words[:-1]
    return words


def parse_request(raw: str) -> ParsedRequest:
    text = " " + raw.lower().replace("\u00a0", " ") + " "

    lo, hi, text = _extract_budget(text)

    soft_m = _SOFT.search(text)
    hard, soft = (text[:soft_m.start()], text[soft_m.start():]) if soft_m else (text, "")

    reqs, tokens, extras, hard = _extract_specs(hard)
    conditions, hard = _extract_conditions(hard)

    gpu = None
    m = _GPU.search(hard)
    if m:
        gpu = _gpu_key(m)
        hard = _cut(hard, m)
    cpu = extract_cpu(hard)
    if cpu:
        for pat, _ in _CPU_PATTERNS:
            hard = pat.sub(" ", hard)
        hard = re.sub(r"\b(?:intel|amd|apple|processador)\b", " ", hard)

    brands = find_brands(hard)
    soft_brands = [b for b in find_brands(soft) if b not in brands]
    if len(brands) > 1:                           # várias marcas: filtram-se depois, não vão ao termo
        for s, e in reversed(brand_spans(hard)):
            hard = hard[:s] + " " + hard[e:]

    color_words = [w for w in re.findall(r"[a-zçãõáéíóú]+", hard + " " + soft) if w in _COLORS]
    extras += [c for c in color_words if c not in extras]
    hard = " ".join(w for w in hard.split() if w.strip(",;") not in _COLORS)

    nice = [re.sub(r"\s+", " ", soft).strip(" ,;.")] if soft.strip() else []

    # --- nome do artigo: o que vem antes de "com / que / para / sem / vírgula" ---
    head = _HEAD_END.split(hard, maxsplit=1)[0]
    words = _strip_words([w.strip(",;.") for w in head.split() if w.strip(",;.")])
    non_label = [w for w in words if w not in _LABELS]
    if non_label and infer_wanted_category(" ".join(non_label)) in ("laptop", "desktop_pc"):
        words = non_label                        # "portátil ram ssd": as etiquetas não são o artigo
    if len(brands) == 1:
        if any(find_brands(w) for w in words):   # "placa gráfica da msi": tira o "da" antes da marca
            words = [w for i, w in enumerate(words)
                     if not (w in _TRAIL_FILLERS and i + 1 < len(words) and find_brands(words[i + 1]))]
        else:
            words.append(brands[0].split()[0])   # marca única fora do nome: ajuda a pesquisa na loja
    base_words = [w for w in words if w not in _TRAIL_FILLERS]

    category = infer_wanted_category(" ".join(words) + (f" {gpu}" if gpu else ""))
    if category is None and "ram" in words:
        category = "ram"

    # "29 polegadas" numa bicicleta não é um ecrã: só vira requisito em artigos com ecrã.
    has_screen_item = category in ("monitor", "laptop") or re.search(
        r"\b(?:ecr[ãa]|ecran|tela|display|tv|televis[ãa]o|telem[óo]vel|smartphone|tablet)\b", raw.lower())
    if not has_screen_item and any(r.attribute == "screen_inches" for r in reqs):
        reqs = [r for r in reqs if r.attribute != "screen_inches"]
        if tokens.get("screen"):
            words.append(tokens.pop("screen"))

    keep = {"monitor": "screen", "ssd": "storage", "ram": "ram", "laptop": "ram", "desktop_pc": "ram"}.get(category or "")
    if keep and tokens.get(keep):
        words.append(tokens[keep])
    if gpu and gpu not in " ".join(words):
        words.append(gpu)

    term = " ".join(dict.fromkeys(words)).strip()
    needs_llm = (not base_words and not gpu) or len(base_words) > MAX_TERM_WORDS
    if not term:
        term = clean_search_term(raw)

    return ParsedRequest(
        raw=raw, term=term, max_budget=hi, min_budget=lo, conditions=conditions, brands=brands,
        soft_brands=soft_brands, cpu=cpu, gpu=gpu, requirements=reqs, extras=extras,
        nice_to_have=nice, needs_llm_term=needs_llm,
    )


def finalize_request(req: ParsedRequest, eq) -> tuple[ParsedRequest, ProductSpecs]:
    """Junta o que as regras apanharam com o que o LLM (Grupo 1) devolveu.
    As regras mandam em orçamento e em requisitos numéricos; o LLM completa o resto."""
    max_b = req.max_budget if req.max_budget is not None else eq.query.max_budget
    merged = req.model_copy(update={"max_budget": max_b})

    covered = {canonical_attribute(r.attribute) for r in req.requirements}
    own_chips = {re.sub(r"\s+", "", c.lower()) for c in (req.gpu, req.cpu) if c}
    kept: list[Requirement] = []
    for r in eq.specs.requirements:
        if is_numeric_requirement(r) and canonical_attribute(r.attribute) in covered:
            continue                                          # já apanhado pelas regras
        value = re.sub(r"\s+", "", r.value.lower())
        if any(c and c in value for c in own_chips):
            continue                                          # gpu/cpu já tratados à parte
        kept.append(r)
    specs = ProductSpecs(category=eq.specs.category, requirements=req.requirements + kept)
    return merged, specs


def describe(req: ParsedRequest) -> str:
    """Resumo legível do que foi percebido do pedido (para mostrar ao utilizador)."""
    parts = [f"termo: {req.term}"]
    if req.min_budget or req.max_budget:
        if req.min_budget and req.max_budget:
            parts.append(f"orçamento: {req.min_budget:g} a {req.max_budget:g} €")
        elif req.max_budget:
            parts.append(f"orçamento: até {req.max_budget:g} €")
        else:
            parts.append(f"orçamento: a partir de {req.min_budget:g} €")
    if req.conditions:
        parts.append("estado: " + "/".join(req.conditions))
    if req.brands:
        parts.append("marca: " + " ou ".join(req.brands))
    if req.cpu:
        parts.append(f"processador: {req.cpu}")
    if req.requirements:
        parts.append("requisitos: " + ", ".join(
            f"{r.attribute} {r.operator} {r.value}" for r in req.requirements))
    pref = req.soft_brands + req.extras
    if pref:
        parts.append("preferências: " + ", ".join(pref))
    return " | ".join(parts)
