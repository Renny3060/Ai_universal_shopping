from backend.agents.group3_logic.vertical_rules import detect_vertical


def test_tech():
    assert detect_vertical("RTX 5060 até 500€") == "tech"


def test_moto():
    assert detect_vertical("capacete modular") == "moto"
    assert detect_vertical("Yamaha MT-07 até 6000€") == "moto"


def test_cars():
    assert detect_vertical("golf gti até 12000€") == "cars"
    assert detect_vertical("BMW serie 1") == "cars"


def test_desconhecido_devolve_none():
    assert detect_vertical("cadeira de escritório") is None