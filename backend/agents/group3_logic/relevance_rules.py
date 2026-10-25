"""Filtro geral de "isto não é o artigo que pediste", para TODAS as lojas.

Problema: o título tem a palavra pesquisada mas o artigo é outro (carro de brinquedo "Audi TT",
mala "para monitor 24", capa "para iPhone"). Duas regras determinísticas, sem LLM:

1. Contexto de acessório: se nenhuma palavra do pedido aparece ANTES de "para / compatível com /
   for / pour...", o título descreve um acessório desse artigo. "Mala Portátil para Monitor 24"
   (pedido "monitor 24") é rejeitada; "Monitor 24 para escritório" e "Memória RAM para portátil"
   (pedido "memória RAM") ficam.
2. Brinquedos, miniaturas e merchandising: palavras como brinquedo, miniatura, escala 1:18, lego,
   poster, autocolante. Só contam se o pedido não as menciona (quem pesquisa "lego" quer lego) e
   não se aplicam na vertical "general" (lojas de brinquedos e de casa).

Nada disto é por loja: funciona igual em qualquer loja nova."""
import re
import unicodedata
from typing import Optional

from backend.schemas.ranking import RankedProduct, RejectedProduct
from backend.utils.query_cleaning import clean_search_term

_STOPWORDS = {"de", "da", "do", "das", "dos", "para", "com", "the", "and", "por", "um", "uma",
              "em", "ate", "mais", "menos", "max", "maximo", "euros", "euro"}

_ACCESSORY_MARKER = re.compile(
    r"\b(?:para|pra|compativel(?:\s+com)?|compatible(?:\s+with)?|for|pour|fits|suitable\s+for|"
    r"adaptavel|destinado\s+a)\b"
)

# Palavras (já sem acentos, minúsculas) de artigos que NÃO são o produto principal.
_TOY_WORDS = [
    "brinquedo", "brinquedos", "juguete", "juguetes", "toy", "toys", "miniatura", "miniaturas",
    "maqueta", "maquete", "lego", "playmobil", "hot wheels", "matchbox", "diecast", "die-cast",
    "die cast", "telecomandado", "peluche", "boneco", "bonecos", "boneca", "bonecas", "figura de acao",
]
_MERCH_WORDS = [
    "poster", "posters", "autocolante", "autocolantes", "sticker", "stickers", "adesivo", "adesivos",
    "puzzle", "funko", "porta-chaves", "porta chaves", "chaveiro", "chaveiros", "keychain",
    "t-shirt", "tshirt", "caneca", "canecas",
]
# Escala de modelos: 1:18, 1/24, 1:43... (não apanha 16:9 nem 21:9)
_SCALE = re.compile(r"(?<![\d:/])1\s?[:/]\s?(?:8|10|12|14|16|18|20|24|32|36|43|64|87)(?![\d])")

_GROUPS = [
    ("brinquedo ou miniatura", _TOY_WORDS),
    ("merchandising", _MERCH_WORDS),
]


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def query_words(wanted_text: str) -> list[str]:
    """Palavras significativas do pedido (sem orçamento, stopwords nem palavras de 1 a 2 letras)."""
    q = _fold(clean_search_term(wanted_text or ""))
    return [w for w in re.findall(r"[a-z0-9]+", q)
            if len(w) >= 3 and w not in _STOPWORDS and not w.isdigit()]


def _stem(w: str) -> str:
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


def _word_in(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) is not None


def _asks_for(query_norm: str, word: str) -> bool:
    return _stem(word) in query_norm


def _accessory_reason(title_norm: str, words: list[str]) -> Optional[str]:
    """Rejeita quando nenhuma palavra do pedido aparece antes do "para"/"compatível com"."""
    if not words:
        return None
    m = _ACCESSORY_MARKER.search(title_norm)
    if not m:
        return None
    head = title_norm[:m.start()]
    if any(_stem(w) in head for w in words):
        return None
    tail = title_norm[m.end():]
    if not any(_stem(w) in tail for w in words):
        return None
    return f"acessório \"{m.group(0)}\" (a palavra pedida só aparece depois de \"{m.group(0)}\")"


def _non_item_reason(title_norm: str, query_norm: str, vertical: Optional[str]) -> Optional[str]:
    if vertical == "general":
        return None
    for label, words in _GROUPS:
        for w in words:
            if _word_in(title_norm, w) and not _asks_for(query_norm, w):
                return f"{label} (\"{w}\")"
    asks_toy = any(_asks_for(query_norm, w) for w in _TOY_WORDS)
    if _SCALE.search(title_norm) and not asks_toy and not re.search(r"\b(?:escala|1[:/]\d+)\b", query_norm):
        return "brinquedo ou miniatura (escala de modelo)"
    return None


def reason_for(title: str, wanted_text: str, vertical: Optional[str] = None) -> Optional[str]:
    t = _fold(title)
    q = _fold(wanted_text or "")
    words = query_words(wanted_text)
    return _accessory_reason(t, words) or _non_item_reason(t, q, vertical)


def split_not_the_item(
    items: list[RankedProduct], wanted_text: str, vertical: Optional[str] = None,
) -> tuple[list[RankedProduct], list[RejectedProduct]]:
    """(mantidos, rejeitados). Sem texto de pedido não filtra nada."""
    if not (wanted_text or "").strip():
        return items, []
    keep: list[RankedProduct] = []
    out: list[RejectedProduct] = []
    for it in items:
        why = reason_for(it.product.title, wanted_text, vertical)
        if why:
            out.append(RejectedProduct(product=it.product, reason=f"não é o artigo pedido: {why}"))
        else:
            keep.append(it)
    return keep, out
