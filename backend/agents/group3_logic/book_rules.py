"""Lojas de livros (kind == "books") em pesquisas que não pedem livros.

Numa pesquisa como "lego ninjago", a Bertrand e a Almedina devolvem livros do tema. Não são
removidos (podem interessar), mas ficam marcados e passam DEPOIS dos restantes no ranking,
a não ser que o pedido fale de livros.
"""
import re
import unicodedata

from backend.agents.group3_logic.scoring_agent import BOOK_WARNING
from backend.schemas.ranking import RankedProduct

BOOK_WORDS = [
    "livro", "livros", "book", "books", "ebook", "romance", "romances", "manual", "manuais",
    "bd", "banda desenhada", "comic", "comics", "manga", "mangas", "colorir", "audiolivro",
    "ler", "leitura", "autor", "isbn",
]


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def wants_books(wanted_text: str) -> bool:
    t = _norm(wanted_text)
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in BOOK_WORDS)


def mark_books(items: list[RankedProduct], wanted_text: str, stores_cfg: dict) -> list[RankedProduct]:
    """Acrescenta BOOK_WARNING aos itens de lojas de livros, se o pedido não é sobre livros."""
    if wants_books(wanted_text):
        return items
    for it in items:
        if stores_cfg.get(it.product.store, {}).get("kind") == "books":
            if BOOK_WARNING not in it.warnings:
                it.warnings.append(BOOK_WARNING)
    return items
