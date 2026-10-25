import pytest


@pytest.fixture(autouse=True)
def sem_llm_nas_categorias(monkeypatch):
    """Os testes não dependem do Ollama: sem resposta do LLM, o validador usa as regras."""
    monkeypatch.setattr(
        "backend.agents.group3_logic.validator_agent.classify_titles",
        lambda titles: {},
    )