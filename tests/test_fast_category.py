from backend.agents.group3_logic.fast_category import fast_classify


def test_lead_words():
    assert fast_classify("Portátil HP 15-FC0097NP 15.6 R7 16GB 1TB SSD") == "laptop"
    assert fast_classify("Notebook Lenovo IdeaPad 3") == "laptop"
    assert fast_classify("Pc Gaming RTX 5060 Ryzen 5") == "desktop_pc"
    assert fast_classify("Memória RAM Kingston Fury Beast 16GB DDR4") == "ram"
    assert fast_classify("Kit Memória DDR5 32GB Corsair Vengeance") == "ram"
    assert fast_classify("SSD Kingston NV2 1TB") == "ssd"
    assert fast_classify("Disco SSD Samsung 990 EVO 1TB") == "ssd"
    assert fast_classify("Placa Gráfica MSI RTX 5060") == "graphics_card"
    assert fast_classify("Processador AMD Ryzen 5 5600") == "cpu"
    assert fast_classify("Monitor LG 27 IPS") == "monitor"


def test_ambiguous_goes_to_llm():
    assert fast_classify("Memória RAM para Portátil") == "ram"          # começa por memória RAM
    assert fast_classify("Mala para Portátil 15.6") is None              # acessório
    assert fast_classify("Portátil Mala Preta 15.6") is None             # palavra de acessório
    assert fast_classify("Portátil Lenovo Thinkcentre M70s SFF Intel Core i5") is None   # é um desktop
    assert fast_classify("Fonte de Alimentação AC 245W para Laptop Lenovo") is None      # carregador
    assert fast_classify("Disco Externo 1TB USB-C") is None
    assert fast_classify("Celular Portátil Mini Smartphone") is None
