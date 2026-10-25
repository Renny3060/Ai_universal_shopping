from backend.agents.group2_search import aggregator
from backend.agents.group2_search.aggregator import NO_RESULTS, search_all


def test_loja_vazia_devolve_mensagem_neutra(monkeypatch):
    class Vazio:
        def __init__(self, *a, **k): pass
        def search(self, *a, **k): return []
    monkeypatch.setattr(aggregator, "ConfigurableScraper", Vazio)
    results, errors = search_all("xyz", stores=["pcdiga"], save=False, use_cache=False)
    assert results == [] and errors == {"pcdiga": NO_RESULTS}


def test_excecao_continua_a_ser_erro(monkeypatch):
    class Falha:
        def __init__(self, *a, **k): pass
        def search(self, *a, **k): raise RuntimeError("bloqueado: x")
    monkeypatch.setattr(aggregator, "ConfigurableScraper", Falha)
    _, errors = search_all("xyz", stores=["pcdiga"], save=False, use_cache=False)
    assert errors["pcdiga"].startswith("RuntimeError")