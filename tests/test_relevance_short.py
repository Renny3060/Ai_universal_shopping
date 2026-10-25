from backend.agents.group2_search.aggregator import relevant


def test_sigla_de_duas_letras_exigida_com_varias_palavras():
    assert relevant("Audi TT 1.8 T Coupé", "audi tt")
    assert relevant("Audi TT-RS Roadster", "audi tt")
    assert not relevant("Audi A3 Sportback 2.0 TDI", "audi tt")
    assert not relevant("Audi Q7 3.0 TDI", "audi tt")
    assert not relevant("Audi TTS Coupé", "audi tt")


def test_sigla_com_numeros_soltos():
    assert relevant("Audi TT 2.0 TFSI", "audi tt 2.0")
    assert not relevant("Audi A4 2.0 TDI", "audi tt 2.0")


def test_modelos_com_digitos_nao_mudam():
    assert relevant("BMW X5 xDrive30d", "bmw x5")
    assert not relevant("BMW X3 xDrive", "bmw x5")
    assert relevant("Radeon RX7600 8GB", "rx 7600")
    assert relevant("Placa MSI RTX 5060Ti 16GB", "rtx 5060 ti")


def test_siglas_genericas_e_palavra_unica_nao_filtram():
    assert relevant("Monitor Samsung 27 polegadas", "monitor tv")
    assert relevant("Audi A3 Sportback", "tt")
    assert relevant("Golf GTI 2.0", "golf gti")


def test_trust_words_nao_aplica_siglas():
    assert relevant("Capacete NOLAN N120", "capacete tt", trust_words=True)
