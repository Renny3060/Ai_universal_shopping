from backend.agents.group3_logic.categories import (
    add_category_hint,
    build_search_term,
    category_hint,
)


def test_acrescenta_placa_grafica():
    assert build_search_term("RTX 5060 até 500€") == "placa grafica RTX 5060"


def test_nao_duplica_se_ja_tem():
    assert build_search_term("placa gráfica RTX 5060 até 500€") == "placa gráfica RTX 5060"


def test_categoria_desconhecida_nao_muda():
    assert build_search_term("rtc 5060") == "rtc 5060"


def test_outra_categoria_nao_muda():
    assert build_search_term("monitor 27 polegadas até 200€") == "monitor 27 polegadas"


def test_hint_com_termo_das_keywords():
    assert add_category_hint("RTX 5060", "RTX 5060 até 500€") == "placa grafica RTX 5060"


def test_category_hint_devolve_palavra():
    assert category_hint("RTX 5060", "RTX 5060 até 500€") == "placa grafica"


def test_category_hint_none_se_ja_tem_ou_sem_categoria():
    assert category_hint("placa gráfica RTX 5060", "placa gráfica RTX 5060") is None
    assert category_hint("rtc 5060", "rtc 5060") is None