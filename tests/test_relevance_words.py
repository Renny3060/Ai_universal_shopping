from backend.agents.group2_search.aggregator import relevant


def test_palavras_sem_numeros_filtram():
    assert relevant("VW Golf 2.0 GTI DSG", "golf gti")
    assert not relevant("VW Golf", "golf gti")
    assert not relevant("VW Bora", "golf gti")


def test_plural_e_acentos():
    assert relevant("Capacete Integral Arai", "capacetes")
    assert relevant("Placa Gráfica Asus", "placa grafica")


def test_termos_com_numeros_nao_mudam():
    assert relevant("Palit GeForce RTX 5060 Dual", "rtx 5060")
    assert not relevant("Palit GeForce RTX 5060 Ti", "rtx 5060")

def test_trust_words_nao_exige_cada_palavra():
    from backend.agents.group2_search.aggregator import relevant
    assert not relevant("Capacete NOLAN N120-1 Classico", "capacete modular")
    assert relevant("Capacete NOLAN N120-1 Classico", "capacete modular", trust_words=True)


def test_trust_words_mantem_numeros_de_modelo():
    from backend.agents.group2_search.aggregator import relevant
    assert not relevant("Placa RTX 4060", "rtx 5060", trust_words=True)

def test_trust_words_exige_pelo_menos_uma_palavra():
    from backend.agents.group2_search.aggregator import relevant
    assert not relevant("Kit de parafusos GIVI 01VKIT", "golf gti", trust_words=True)
    assert relevant("Capacete NOLAN N120-1 Classico", "capacete modular", trust_words=True)