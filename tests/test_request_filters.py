from backend.agents.group1_input.request_parser import ParsedRequest, parse_request
from backend.agents.group3_logic.request_filters import apply_request_filters, apply_soft_preferences
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def _item(title, price=500.0, condition="new", score=50.0):
    p = ProductResult(store="worten", external_id=title, title=title,
                      url="https://www.worten.pt/p/1", price=price, condition=condition)
    return RankedProduct(product=p, total_cost=price, score=score)


def _req(text):
    return parse_request(text)


def test_estado_pedido_rejeita_os_outros():
    ok, rej = apply_request_filters(
        [_item("Portátil A", condition="new"), _item("Portátil B", condition="used")],
        _req("portátil novo até 900€"))
    assert [i.product.title for i in ok] == ["Portátil A"]
    assert rej[0].reason.startswith("estado diferente")


def test_marca_diferente_rejeita_e_sem_marca_avisa():
    ok, rej = apply_request_filters(
        [_item("Portátil Asus TUF"), _item("Portátil Lenovo IdeaPad"), _item("Portátil 15.6 genérico"),
         _item("Portátil ROG Strix")],
        _req("portátil asus ou hp até 900€"))
    assert [i.product.title for i in ok] == ["Portátil Asus TUF", "Portátil 15.6 genérico", "Portátil ROG Strix"]
    assert rej[0].reason.startswith("marca diferente")
    assert any("Marca não confirmada" in w for w in ok[1].warnings)
    assert not ok[0].warnings


def test_processador_diferente_rejeita_e_desconhecido_avisa():
    ok, rej = apply_request_filters(
        [_item("Portátil Intel Core i7-13620H"), _item("Portátil Intel Core i5-1235U"), _item("Portátil sem cpu")],
        _req("portátil com i7 até 1500€"))
    assert [i.product.title for i in ok] == ["Portátil Intel Core i7-13620H", "Portátil sem cpu"]
    assert rej[0].reason.startswith("processador diferente")
    assert any("Processador não confirmado" in w for w in ok[1].warnings)


def test_orcamento_minimo():
    ok, rej = apply_request_filters(
        [_item("Portátil barato", price=300), _item("Portátil bom", price=700)],
        _req("portátil mais de 500€ até 900€"))
    assert [i.product.title for i in ok] == ["Portátil bom"]
    assert "orçamento mínimo" in rej[0].reason


def test_sem_pedido_especial_nao_filtra_nada():
    items = [_item("Portátil A"), _item("Portátil B", condition="used")]
    ok, rej = apply_request_filters(items, _req("portátil até 900€"))
    assert len(ok) == 2 and rej == []


def test_preferencias_dao_bonus_e_reordenam():
    a = _item("Portátil HP preto", score=60.0)
    b = _item("Portátil Samsung branco", score=55.0)
    out = apply_soft_preferences([a, b], _req("portátil até 900€, de preferência da Samsung"))
    assert out[0].product.title == "Portátil Samsung branco" and out[0].score == 63.0
    out = apply_soft_preferences([_item("A", score=60.0), _item("B preto", score=57.0)],
                                 _req("portátil preto até 900€"))
    assert out[0].product.title == "B preto" and out[0].score == 61.0


def test_barato_ignora_bonus():
    a, b = _item("A", score=60.0), _item("B preto", score=50.0)
    out = apply_soft_preferences([a, b], _req("portátil preto até 900€"), sort="cheapest")
    assert [i.score for i in out] == [60.0, 50.0]
