from backend.agents.group3_logic.categories import classify_title


def test_modulos_de_ram_sem_a_expressao_memoria_ram():
    for t in (
        "Patriot Signature Line PSD416G26662S 16GB 1x16GB DDR4 2666MHz",
        "DDR4 SODIMM PNY 16GB CL22 3200",
        "Lexar Ddr4 Sodimm 16gb(1*16gb) /3200 Cl22",
        "PNY Performance 16GB DDR4 3200MHz CL22 Black",
    ):
        assert classify_title(t) == "ram", t


def test_computadores_e_placas_nao_viram_ram():
    assert classify_title("Portátil ASUS 15.6 Intel Core i5 16GB DDR4 3200MHz") == "laptop"
    assert classify_title("Asus Vivobook Intel Core i5 16GB DDR4 3200MHz 512GB") is None
    assert classify_title("Placa Gráfica ZOTAC RTX 5060 8GB GDDR7") == "graphics_card"
    assert classify_title("Placa-Mãe ASUS PRIME A320M-K DDR4") == "motherboard"
