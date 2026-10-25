import time

from backend.agents.group2_search import aggregator
from backend.agents.group2_search.aggregator import NOT_REACHED_MSG, TIMEOUT_MSG, search_all
from backend.agents.group3_logic import category_llm as m
from backend.schemas.product import ProductResult


def _item(store):
    return ProductResult(store=store, external_id="1", title="Placa RTX 5060 teste",
                         url=f"https://www.{store}.pt/p/1", price=300.0)


def _patch(monkeypatch, slow=()):
    class Fake:
        def __init__(self, name, cfg):
            self.name = name

        def search(self, *a, **k):
            if self.name in slow:
                time.sleep(2.0)
            return [_item(self.name)]

    monkeypatch.setattr(aggregator, "ConfigurableScraper", Fake)


def test_loja_lenta_e_largada_e_as_rapidas_ficam(monkeypatch):
    _patch(monkeypatch, slow={"worten"})
    t0 = time.monotonic()
    results, errors = search_all("RTX 5060", stores=["pcdiga", "worten"], save=False,
                                 use_cache=False, time_budget=0.4)
    assert time.monotonic() - t0 < 1.5
    assert [r.store for r in results] == ["pcdiga"]
    assert errors == {"worten": TIMEOUT_MSG}


def test_loja_em_fila_nao_chega_a_ser_pesquisada(monkeypatch):
    _patch(monkeypatch, slow={"worten"})
    monkeypatch.setattr(aggregator, "MAX_WORKERS", 1)
    results, errors = search_all("RTX 5060", stores=["worten", "pcdiga"], save=False,
                                 use_cache=False, time_budget=0.4)
    assert results == []
    assert errors == {"worten": TIMEOUT_MSG, "pcdiga": NOT_REACHED_MSG}


def test_sem_limite_espera_por_todas(monkeypatch):
    _patch(monkeypatch)
    results, errors = search_all("RTX 5060", stores=["pcdiga", "worten"], save=False,
                                 use_cache=False, time_budget=None)
    assert len(results) == 2 and errors == {}


def test_llm_sem_tempo_nao_chama_o_modelo(monkeypatch):
    monkeypatch.setattr(m, "get_cached", lambda key: None)
    monkeypatch.setattr(m, "set_cached", lambda *a, **k: None)

    def nao_deve_chamar(chunk):
        raise AssertionError("não devia chamar o LLM")

    monkeypatch.setattr(m, "_ask", nao_deve_chamar)
    assert m.classify_titles(["a1", "b2"], time_budget=0) == {}
    assert m.LAST_RUN["skipped_titles"] == 2
    assert m.LAST_RUN["failed_titles"] == 0


def test_titulos_largados_ficam_marcados_e_nao_se_repetem(monkeypatch):
    guardados = {}
    monkeypatch.setattr(m, "get_cached", lambda key: guardados.get(key))
    monkeypatch.setattr(m, "set_cached", lambda key, store, payload, ttl_minutes=None: guardados.update({key: payload}))

    def nao_deve_chamar(chunk):
        raise AssertionError("não devia chamar o LLM")

    monkeypatch.setattr(m, "_ask", nao_deve_chamar)
    assert m.classify_titles(["a1", "b2"], time_budget=0) == {}
    assert all(v["category"] == m.SKIP_MARK for v in guardados.values()) and len(guardados) == 2
    # segunda chamada, mesmo com tempo de sobra: respeita o marcador e não chama o LLM
    assert m.classify_titles(["a1", "b2"], time_budget=30) == {}
    assert m.LAST_RUN["skipped_titles"] == 2


def test_nao_comeca_lote_que_passaria_do_limite(monkeypatch):
    from types import SimpleNamespace as NS
    monkeypatch.setattr(m, "get_cached", lambda key: None)
    monkeypatch.setattr(m, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(m, "BATCH_SIZE", 1)
    chamadas = []

    def lento(chunk):
        chamadas.append(chunk)
        time.sleep(0.3)
        return NS(items=[NS(id=0, category="laptop")])

    monkeypatch.setattr(m, "_ask", lento)
    out = m.classify_titles(["a1", "b2", "c3"], time_budget=0.5)
    assert len(chamadas) == 1          # o 2.º lote (0.3 s) passaria dos 0.5 s: não arranca
    assert out == {"a1": "laptop"}
    assert m.LAST_RUN["skipped_titles"] == 2


def test_timeout_do_ollama_nao_insiste_nos_lotes_seguintes(monkeypatch):
    monkeypatch.setattr(m, "get_cached", lambda key: None)
    monkeypatch.setattr(m, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(m, "BATCH_SIZE", 1)
    chamadas = []

    def timeout(chunk):
        chamadas.append(chunk)
        raise TimeoutError("timed out")

    monkeypatch.setattr(m, "_ask", timeout)
    assert m.classify_titles(["a1", "b2", "c3"], time_budget=None) == {}
    assert len(chamadas) == 1
    assert m.LAST_RUN["failed_titles"] == 1
    assert m.LAST_RUN["skipped_titles"] == 2


def test_cada_pedido_ao_llm_tem_limite_proprio(monkeypatch):
    vistos = {}

    def falso(system, user, schema, temperature=0.0, timeout=None):
        vistos["timeout"] = timeout
        return schema(items=[])

    monkeypatch.setattr(m, "ask_structured", falso)
    m._ask(["a1"])
    assert vistos["timeout"] == m.CALL_TIMEOUT_S


def test_lotes_pequenos_e_modelo_mantido_em_memoria():
    from backend.agents import llm
    assert m.BATCH_SIZE <= 10
    assert llm.KEEP_ALIVE
