from backend.agents.group2_search import aggregator
from backend.agents.group3_logic import category_llm


def test_orcamentos_somados_ficam_abaixo_de_10_min():
    # lojas + LLM + 1 pedido ao Ollama a passar do limite < 600 s
    total = aggregator.SCRAPE_BUDGET_S + category_llm.TIME_BUDGET_S + category_llm.CALL_TIMEOUT_S
    assert total <= 600


def test_limite_deixou_de_ser_2_min():
    assert aggregator.SCRAPE_BUDGET_S > 70
    assert category_llm.TIME_BUDGET_S > 30


def test_lotes_de_10_e_keep_alive():
    from backend.agents import llm
    assert category_llm.BATCH_SIZE == 10
    assert llm.KEEP_ALIVE == "30m"
