import pytest


@pytest.fixture(autouse=True)
def category_llm_formato_normal(monkeypatch):
    """Os testes antigos da classificação por LLM assumem a resposta em objetos {id, category}.
    O formato compacto (ligado por defeito) tem os seus testes próprios, que o ativam."""
    monkeypatch.setattr("backend.agents.group3_logic.category_llm.COMPACT_OUTPUT", False)
