from backend.agents.group3_logic.book_rules import mark_books, wants_books
from backend.agents.group3_logic.scoring_agent import BOOK_WARNING, rank
from backend.agents.group2_search.stores import STORES
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct

CFG = {"bertrand": {"kind": "books"}, "olx": {}}


def _item(store, price, title="Lego Ninjago"):
    p = ProductResult(store=store, external_id=store + str(price), title=title,
                      url="https://x.pt/1", price=price)
    return RankedProduct(product=p, shipping=None, taxes=0.0, total_cost=price,
                         category=None, score=0.0, warnings=[])


def test_lojas_de_livros_marcadas():
    items = mark_books([_item("bertrand", 5.0), _item("olx", 8.0)], "lego ninjago", CFG)
    assert BOOK_WARNING in items[0].warnings and BOOK_WARNING not in items[1].warnings


def test_pedido_de_livros_nao_marca():
    items = mark_books([_item("bertrand", 5.0)], "livro lego ninjago", CFG)
    assert BOOK_WARNING not in items[0].warnings


def test_wants_books():
    assert wants_books("romance policial") and wants_books("Banda Desenhada")
    assert not wants_books("lego ninjago")


def test_livros_ficam_depois_no_ranking():
    items = mark_books([_item("bertrand", 4.0), _item("olx", 9.0)], "lego ninjago", CFG)
    for sort in ("best_value", "cheapest"):
        assert rank(list(items), sort)[0].product.store == "olx"


def test_stores_com_kind_books():
    assert STORES["bertrand"]["kind"] == "books" and STORES["almedina"]["kind"] == "books"
