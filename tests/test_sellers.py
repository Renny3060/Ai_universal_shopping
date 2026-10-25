from backend.agents.group3_logic.sellers import is_external_seller

CFGS = {"worten": {"own_seller_names": ["worten"]}, "pcdiga": {}}


def test_vendedor_externo():
    assert is_external_seller("worten", "LojaWeb", CFGS)


def test_propria_loja_sem_distinguir_maiusculas():
    assert not is_external_seller("worten", "Worten", CFGS)
    assert not is_external_seller("worten", " WORTEN ", CFGS)


def test_vendedor_desconhecido_nao_e_externo():
    assert not is_external_seller("worten", None, CFGS)


def test_loja_sem_own_seller_names():
    assert not is_external_seller("pcdiga", "Qualquer", CFGS)


def test_usa_a_config_real_por_defeito():
    assert is_external_seller("worten", "LojaWeb")