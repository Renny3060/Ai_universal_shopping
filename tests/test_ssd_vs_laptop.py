from backend.agents.group3_logic.categories import classify_title


def test_portatil_sem_a_palavra_portatil_nao_e_ssd():
    assert classify_title("ASUS TUF Gaming A15 RTX 4060 16GB RAM SSD 512GB") != "ssd"
    assert classify_title('Lenovo LOQ 15 Ryzen 5 RTX 4060 16GB SSD 512GB 15.6"') != "ssd"


def test_ssd_verdadeiro_continua_ssd():
    assert classify_title("SSD Kingston NV2 1TB NVMe") == "ssd"
    assert classify_title("Disco SSD 1TB Samsung 870 EVO") == "ssd"
    assert classify_title("Crucial P3 Plus 1TB SSD M.2") == "ssd"


def test_portatil_com_palavra_continua_laptop():
    assert classify_title("Portátil Asus TUF RTX 4060 SSD 512GB") == "laptop"
