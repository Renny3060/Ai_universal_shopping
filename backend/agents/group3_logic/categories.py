import re
from typing import Optional

from backend.utils.query_cleaning import clean_search_term

# Processadores de portátil: ajudam a reconhecer um portátil quando a marca vem à frente
_CPU = (r"\b(?:intel|amd|ryzen|celeron|pentium|snapdragon)\b|core\s*(?:i[3579]|ultra)")
_LAPTOP_WORD = r"\b(?:port[áa]til|laptop|notebook)\b"
_LAPTOP_RULE = (
    r"^\s*(?:(?:computador|pc)\s+)?(?:port[áa]til|laptop|notebook)\b"   # começa por portátil
    rf"|^(?=.*{_LAPTOP_WORD})(?=.*(?:{_CPU}))"                          # ou tem portátil + processador
)

# Ordem importa. Acessórios e impressoras primeiro (só quando o título COMEÇA pela palavra,
# para não apanhar "Carregador de Portátil" como portátil). 'portable_other' fica no fim:
# são os artigos "portáteis" que não são computadores (ventoinhas, colunas, estações de energia...).
TITLE_RULES = [
    ("accessory", r"^\s*(carregador|suporte|mochila|bolsa|capa|base|adaptador|cabo|rato|teclado"
                  r"|bateria|pel[íi]cula|protetor)\b"),
    ("printer", r"^\s*impressora\b"),
    ("laptop", _LAPTOP_RULE),
    ("desktop_pc", r"computador|desktop|\bpc\s+(gaming|gamer)"),
    ("graphics_card", r"placa gr[áa]fica|tarjeta gr[áa]fica|placa de v[íi]deo|graphics card|\bgpu\b"),
    ("cpu", r"processador|processor"),
    ("motherboard", r"placa[- ]m[ãa]e|motherboard"),
    ("ram", r"mem[óo]ria\s+ram"),
    # Módulos de RAM sem a expressão 'memória ram' (ex.: 'Patriot 16GB DDR4 2666MHz'). Só quando o
    # título tem DDR + (MHz, SODIMM, CL, memory) e NÃO tem sinais de computador completo.
    ("ram", r"^(?!.*(?:intel|amd|ryzen|celeron|core\s*i[3579]|ssd|disco|ecr[ãa]|polegada|\d\s?\"))"
            r"(?=.*\bddr[2-5]\b)(?=.*(?:(?<![a-z])mhz\b|so-?dimm|\bdimm\b|udimm|\bcl\d{2}\b|memory))"),
    # SSD/disco só se o título não tiver sinais de computador completo (RAM, GPU, CPU, ecrã):
    # "ASUS TUF A15 RTX 4060 16GB RAM SSD 512GB" é um portátil, não um SSD.
    ("ssd", r"^(?!.*(?:\bram\b|\b(?:rtx|gtx)\s*\d{3,4}|ryzen|core\s*i[3579]|polegada|ecr[ãa]|\d{2}(?:[.,]\d)?\s?(?:\"|pol\b)))"
            r".*(?:\bssd\b|disco)"),
    ("psu", r"fonte de alimenta"),
    ("monitor", r"monitor"),
    ("portable_other", r"port[áa]til"),
]

QUERY_RULES = [
    ("laptop", r"port[áa]til|laptop|notebook"),
    ("desktop_pc", r"\bpc\b|computador|desktop"),
    ("graphics_card", r"placa gr[áa]fica|tarjeta gr[áa]fica|\bgpu\b|gr[áa]fica|\b(rtx|gtx|rx)\s*\d{3,4}|radeon"),
    ("cpu", r"processador|ryzen|core\s*i[3579]"),
    ("motherboard", r"placa[- ]m[ãa]e|motherboard"),
    ("ram", r"mem[óo]ria"),
    ("ssd", r"\bssd\b"),
    ("psu", r"fonte de alimenta"),
    ("monitor", r"monitor"),
]

# Palavra a acrescentar ao termo de pesquisa por categoria (só nas lojas com use_hint=True).
# Só graphics_card foi testado com lojas reais; as outras entram depois de confirmadas.
SEARCH_HINTS = {
    "graphics_card": ("placa grafica", r"placa|gr[áa]fica|\bgpu\b|graphics"),
}


def _classify(text: str, rules) -> Optional[str]:
    t = text.lower()
    for category, pattern in rules:
        if re.search(pattern, t):
            return category
    return None


def classify_title(title: str) -> Optional[str]:
    return _classify(title, TITLE_RULES)


def infer_wanted_category(query_text: str) -> Optional[str]:
    """Categoria que o utilizador procura (None = não filtrar por categoria)."""
    return _classify(query_text, QUERY_RULES)


def category_hint(term: str, request_text: str) -> Optional[str]:
    """Palavra da categoria a acrescentar nas lojas que a pedem, ou None.
    None também quando o termo já a contém."""
    hint = SEARCH_HINTS.get(infer_wanted_category(request_text))
    if hint:
        word, already = hint
        if not re.search(already, term.lower()):
            return word
    return None


def add_category_hint(term: str, request_text: str) -> str:
    """Termo com a dica já colada à frente (útil para testes e scripts)."""
    word = category_hint(term, request_text)
    return f"{word} {term}".strip() if word else term


def build_search_term(text: str) -> str:
    """'RTX 5060 até 500€' -> 'placa grafica RTX 5060'."""
    return add_category_hint(clean_search_term(text), text)