from backend.agents.group2_search.configurable_scraper import ConfigurableScraper as C


def test_outlet_e_caixa_aberta_sao_recondicionados():
    f = C._detect_condition
    assert f("Portátil Gaming LENOVO LOQ 15IAX9-025 (Outlet Caixa Aberta - Intel Core i5)") == "refurbished"
    assert f("HP Omen (Outlet Grade B - Intel Core)") == "refurbished"
    assert f("Portátil Asus Open Box RTX 4060") == "refurbished"


def test_novo_e_usado_inalterados():
    f = C._detect_condition
    assert f("Portátil Gaming Lenovo LOQ RTX 4060") == "new"
    assert f("Portátil usado Asus") == "used"
    assert f("Portátil Asus recondicionado") == "refurbished"
