from backend.agents.group3_logic.categories import classify_title


def test_portateis_reais():
    assert classify_title("Portátil Vanwin 15.6 Intel Pentium Gold 16GB RAM") == "laptop"
    assert classify_title("Computador Portátil ASUS Vivobook 15 Core i5") == "laptop"
    assert classify_title("Computador Portátil HP 250 G9") == "laptop"
    assert classify_title("HP 250 G9 Intel Core i5 16GB RAM 512GB SSD Portátil 15.6") == "laptop"


def test_portatil_sem_processador_no_titulo():
    assert classify_title("Portátil Xiseziuo 15,6 Fhd Ips 16gb Ram") == "laptop"


def test_artigos_portateis_que_nao_sao_computadores():
    assert classify_title("Ventoinha de Pé Portátil Cecotec EnergySilence 1000 FoldAir") == "portable_other"
    assert classify_title("Estação de Energia Portátil EcoFlow TRAIL 300 DC") == "portable_other"
    assert classify_title("Mini Coluna de Ar Portátil Ultraeficiente Levoit Windi Mini") == "portable_other"


def test_categorias_mais_especificas_ganham():
    assert classify_title('Monitor Portátil 15.6" Full HD') == "monitor"
    assert classify_title("SSD Externo Portátil Samsung T7 1TB") == "ssd"
    assert classify_title("Carregador de Portátil Universal Nox 45W") == "accessory"