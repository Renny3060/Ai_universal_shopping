from backend.agents.group2_search.aggregator import relevant
from backend.agents.group3_logic.categories import classify_title


def test_5060_rejeita_ti():
    assert not relevant('Placa Gráfica Zotac RTX 5060 Ti "Blackwell" 8GB', "rtx 5060")


def test_5060_aceita_normal():
    assert relevant('Placa Gráfica MSI GeForce RTX 5060 "Blackwell" Ventus', "rtx 5060")


def test_5060_ti_so_aceita_ti():
    assert relevant("Placa Gráfica Zotac RTX 5060 Ti 8GB", "rtx 5060 ti")
    assert not relevant("Placa Gráfica MSI RTX 5060 Ventus", "rtx 5060 ti")


def test_numero_em_falta_rejeita():
    assert not relevant("Placa Gráfica MSI RTX 5070", "rtx 5060")


def test_tarjeta_grafica_classificada():
    assert classify_title("Tarjeta Grafica Zotac Rtx 5060 Solo 8gb") == "graphics_card"