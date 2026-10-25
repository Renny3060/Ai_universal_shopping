from backend.agents.group3_logic import category_llm as m


def _setup(monkeypatch, fail=False, bad_id=False):
    store, calls = {}, []

    def fake_get(key):
        return store.get(key)

    def fake_set(key, store_name, payload, ttl_minutes=None):
        store[key] = payload

    def fake_ask(system, user, schema, temperature=0.0, timeout=None):
        calls.append(user)
        if fail:
            raise RuntimeError("ollama em baixo")
        n = len(user.splitlines())
        ids = [99] if bad_id else range(n)
        return m.CategoryBatch(items=[m.TitleCategory(id=i, category="graphics_card") for i in ids])

    monkeypatch.setattr(m, "get_cached", fake_get)
    monkeypatch.setattr(m, "set_cached", fake_set)
    monkeypatch.setattr(m, "ask_structured", fake_ask)
    return calls


def test_classifies_and_uses_cache(monkeypatch):
    calls = _setup(monkeypatch)
    assert m.classify_titles(["Placa A", "Placa B"]) == {
        "Placa A": "graphics_card", "Placa B": "graphics_card"}
    assert len(calls) == 1
    m.classify_titles(["Placa A", "Placa B"])
    assert len(calls) == 1          # segunda vez veio da cache


def test_batches(monkeypatch):
    calls = _setup(monkeypatch)
    monkeypatch.setattr(m, "BATCH_SIZE", 2)
    m.classify_titles(["a", "b", "c", "d", "e"])
    assert len(calls) == 3


def test_failure_returns_empty(monkeypatch):
    _setup(monkeypatch, fail=True)
    assert m.classify_titles(["Placa A"]) == {}


def test_ignores_invalid_id(monkeypatch):
    _setup(monkeypatch, bad_id=True)
    assert m.classify_titles(["Placa A"]) == {}