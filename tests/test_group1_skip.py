from backend.agents.group1_input.pipeline import needs_specs
from backend.schemas.search import SearchQuery


def _q(**kw):
    return SearchQuery(product_type="x", keywords=["x"], **kw)


def test_pedido_simples_nao_gasta_llm_nas_especificacoes():
    assert needs_specs("RTX 5060 até 650€", _q()) is False
    assert needs_specs("golf gti até 12000€", _q()) is False


def test_medidas_no_texto_pedem_especificacoes():
    assert needs_specs("portátil com 16GB de RAM até 900€", _q()) is True
    assert needs_specs("SSD 1TB até 100€", _q()) is True
    assert needs_specs('monitor 27" 144Hz', _q()) is True


def test_requisitos_do_parser_pedem_especificacoes():
    assert needs_specs("portátil gaming", _q(must_have=["RTX"])) is True
    assert needs_specs("portátil gaming", _q(nice_to_have=["teclado retroiluminado"])) is True
