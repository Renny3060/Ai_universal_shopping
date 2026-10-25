from backend.utils.query_cleaning import clean_search_term


def test_removes_budget():
    assert clean_search_term("RTX 5060 até 500€") == "RTX 5060"
    assert clean_search_term("rtx 4070 máx 650 euros") == "rtx 4070"
    assert clean_search_term("placa gráfica rtx 5060 por menos de 500") == "placa gráfica rtx 5060"


def test_keeps_specs():
    assert clean_search_term("ssd 1TB nvme") == "ssd 1TB nvme"
    assert clean_search_term("RTX 5060 16GB") == "RTX 5060 16GB"

from backend.utils.query_cleaning import extract_budget


def test_extract_budget_com_palavra_chave():
    assert extract_budget("RTX 5060 até 500€") == 500.0
    assert extract_budget("rtx 4070 máx 650 euros") == 650.0
    assert extract_budget("placa gráfica rtx 5060 por menos de 500") == 500.0
    assert extract_budget("ssd 1TB até 100€") == 100.0


def test_extract_budget_milhares_e_decimais():
    assert extract_budget("portátil até 1.500€") == 1500.0
    assert extract_budget("portátil até 1 500 euros") == 1500.0
    assert extract_budget("monitor ate 249,90€") == 249.9


def test_extract_budget_so_com_moeda():
    assert extract_budget("RTX 5070 900€") == 900.0


def test_extract_budget_sem_orcamento():
    assert extract_budget("RTX 5060 16GB") is None
    assert extract_budget("ssd 1TB nvme") is None
    assert extract_budget("") is None