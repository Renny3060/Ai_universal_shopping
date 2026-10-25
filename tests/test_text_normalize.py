from backend.agents.group2_search.aggregator import relevant
from backend.utils.text_normalize import normalize_title


def test_homoglifos_cirilicos_viram_latinos():
    assert normalize_title("GeForce RTX 5060 \u0422\u0456") == "GeForce RTX 5060 Ti"


def test_titulo_com_cirilico_deixa_de_passar_na_pesquisa_5060():
    raw = "GeForce RTX 5060 \u0422\u0456 RTX5060\u0422\u0456 GB206-300-A1"
    assert relevant(normalize_title(raw), "RTX 5060") is False


def test_mantem_acentos_e_colapsa_espacos():
    assert normalize_title("  Placa   Gráfica\u00a0RTX 5060  ") == "Placa Gráfica RTX 5060"


def test_vazio():
    assert normalize_title("") == ""