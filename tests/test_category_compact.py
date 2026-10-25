import pytest
from pydantic import ValidationError

from backend.agents.group3_logic import category_llm as m


def test_system_compacto_substitui_a_regra_dos_ids():
    assert "mesmo id" not in m.SYSTEM_COMPACT
    assert "id:categoria" in m.SYSTEM_COMPACT
    assert m.SYSTEM_COMPACT != m.SYSTEM


def test_schema_compacto_impoe_tamanho_e_ids():
    s = m._compact_schema(2)
    js = s.model_json_schema()["properties"]["answers"]
    assert js["minItems"] == 2 and js["maxItems"] == 2
    assert s(answers=["0:laptop", "1:ssd"]).answers == ["0:laptop", "1:ssd"]
    with pytest.raises(ValidationError):
        s(answers=["0:laptop"])
    with pytest.raises(ValidationError):
        s(answers=["0:laptop", "5:ssd"])
    with pytest.raises(ValidationError):
        s(answers=["0:laptop", "1:inventada"])


def test_from_compact_usa_o_id_e_ignora_repetidos_e_invalidos():
    r = m._from_compact(["1:ssd", "0:laptop", "1:ram", "9:other", "x:other"], 2)
    assert {(i.id, i.category) for i in r.items} == {(1, "ssd"), (0, "laptop")}


def test_modo_compacto_converte_pelo_id(monkeypatch):
    monkeypatch.setattr(m, "COMPACT_OUTPUT", True)
    vistos = {}

    def falso(system, user, schema, temperature=0.0, timeout=None):
        vistos["system"], vistos["timeout"] = system, timeout
        return schema(answers=["1:ssd", "0:laptop"])

    monkeypatch.setattr(m, "ask_structured", falso)
    r = m._ask(["Portátil X", "SSD Y"])
    assert {(i.id, i.category) for i in r.items} == {(0, "laptop"), (1, "ssd")}
    assert vistos["system"] == m.SYSTEM_COMPACT and vistos["timeout"] == m.CALL_TIMEOUT_S


def test_modo_normal_continua_igual(monkeypatch):
    monkeypatch.setattr(m, "COMPACT_OUTPUT", False)
    chamado = {}

    def falso(system, user, schema, temperature=0.0, timeout=None):
        chamado["schema"] = schema
        return m.CategoryBatch(items=[])

    monkeypatch.setattr(m, "ask_structured", falso)
    m._ask(["a"])
    assert chamado["schema"] is m.CategoryBatch
