import threading
import time

from backend.agents.group2_search import aggregator
from backend.agents.group2_search.aggregator import (
    EMPTY_SUSPECT, NO_RESULTS, NOT_REACHED_MSG, search_all,
)
from backend.schemas.product import ProductResult


def _item(store):
    return ProductResult(store=store, external_id="1", title="SSD 1TB teste",
                         url=f"https://www.{store}.pt/p/1", price=50.0)


def _patch(monkeypatch, log, empty=(), slow=()):
    running = set()
    lock = threading.Lock()

    class Fake:
        def __init__(self, name, cfg):
            self.name = name

        def search(self, *a, **k):
            with lock:
                log.append(("start", self.name, frozenset(running)))
                running.add(self.name)
            if self.name in slow:
                time.sleep(1.0)
            else:
                time.sleep(0.05)
            with lock:
                running.discard(self.name)
                log.append(("end", self.name, frozenset(running)))
            return [] if self.name in empty else [_item(self.name)]

    monkeypatch.setattr(aggregator, "ConfigurableScraper", Fake)


def test_amazon_so_arranca_depois_das_outras_e_sozinha(monkeypatch):
    log = []
    _patch(monkeypatch, log)
    results, errors = search_all("ssd 1tb", stores=["amazon_es", "pcdiga", "worten", "olx"],
                                 save=False, use_cache=False, time_budget=None)
    assert errors == {}
    assert {r.store for r in results} == {"amazon_es", "pcdiga", "worten", "olx"}
    starts = [e for e in log if e[0] == "start"]
    amazon = next(e for e in starts if e[1] == "amazon_es")
    assert amazon[2] == frozenset()                       # nada a correr ao mesmo tempo
    assert starts[-1][1] == "amazon_es"                   # foi a última a arrancar
    ends_others = [i for i, e in enumerate(log) if e[0] == "end" and e[1] != "amazon_es"]
    amazon_start = next(i for i, e in enumerate(log) if e[0] == "start" and e[1] == "amazon_es")
    assert max(ends_others) < amazon_start


def test_loja_solo_vazia_e_suspeita_e_as_outras_continuam_neutras(monkeypatch):
    _patch(monkeypatch, [], empty={"amazon_es", "pcdiga"})
    results, errors = search_all("ssd 1tb", stores=["amazon_es", "pcdiga", "worten"],
                                 save=False, use_cache=False, time_budget=None)
    assert errors == {"amazon_es": EMPTY_SUSPECT, "pcdiga": NO_RESULTS}
    assert [r.store for r in results] == ["worten"]


def test_prazo_esgotado_nas_paralelas_deixa_a_solo_por_pesquisar(monkeypatch):
    _patch(monkeypatch, [], slow={"worten"})
    results, errors = search_all("ssd 1tb", stores=["worten", "amazon_es"], save=False,
                                 use_cache=False, time_budget=0.3)
    assert errors["amazon_es"] == NOT_REACHED_MSG
    assert "worten" in errors
    assert results == []


def test_so_loja_solo_corre_normalmente(monkeypatch):
    _patch(monkeypatch, [])
    results, errors = search_all("ssd 1tb", stores=["amazon_es"], save=False,
                                 use_cache=False, time_budget=None)
    assert [r.store for r in results] == ["amazon_es"] and errors == {}
