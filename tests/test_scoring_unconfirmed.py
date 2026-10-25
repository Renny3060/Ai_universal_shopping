from types import SimpleNamespace as NS

from backend.agents.group3_logic.scoring_agent import UNCONFIRMED_WARNING, rank


def _item(cost, warnings=()):
    return NS(total_cost=cost, product=NS(condition="new"), warnings=list(warnings), score=0.0)


def test_categoria_nao_confirmada_fica_depois_dos_confirmados():
    confirmado = _item(150.0)
    duvidoso = _item(100.0, [UNCONFIRMED_WARNING])   # mais barato e com melhor score, mas sem categoria confirmada
    out = rank([duvidoso, confirmado])
    assert out == [confirmado, duvidoso]


def test_tambem_no_mais_barato():
    confirmado = _item(150.0)
    duvidoso = _item(100.0, [UNCONFIRMED_WARNING])
    assert rank([duvidoso, confirmado], sort="cheapest") == [confirmado, duvidoso]


def test_dentro_de_cada_grupo_mantem_a_ordem_por_preco():
    a, b = _item(100.0), _item(200.0)
    c, d = _item(50.0, [UNCONFIRMED_WARNING]), _item(80.0, [UNCONFIRMED_WARNING])
    assert rank([d, b, c, a], sort="cheapest") == [a, b, c, d]
    assert rank([d, b, c, a]) == [a, b, c, d]
