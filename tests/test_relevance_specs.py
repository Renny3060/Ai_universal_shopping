from backend.agents.group2_search.aggregator import relevant


def test_capacidade_nao_exigida_no_titulo():
    assert relevant("Portátil Asus Vivobook 15 Intel Core i5", "portátil com 16GB de RAM")


def test_capacidade_com_espaco_passa():
    assert relevant("Portátil HP 16 GB RAM 512 GB SSD", "portátil com 16GB de RAM")


def test_numero_de_modelo_continua_obrigatorio():
    assert relevant("Placa Gráfica RTX 5060 8GB GDDR7", "rtx 5060 8gb")
    assert not relevant("Placa Gráfica RTX 4060 8GB GDDR7", "rtx 5060 8gb")