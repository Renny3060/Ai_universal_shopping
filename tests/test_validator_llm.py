from backend.agents.group3_logic import validator_agent as v
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct

TITLE = "Backplate para Placa Gráfica NVIDIA RTX 5060"   # o regex diz graphics_card


def _item(title=TITLE):
    p = ProductResult(store="x", external_id="1", title=title,
                      url="https://x.com/1", price=100.0)
    return RankedProduct(product=p, total_cost=100.0)


def test_llm_category_wins_over_regex(monkeypatch):
    monkeypatch.setattr(v, "classify_titles", lambda titles: {TITLE: "other"})
    ok, rejected = v.validate([_item()], "graphics_card", None)
    assert ok == []
    assert "via LLM" in rejected[0].reason


def test_fallback_to_regex_when_llm_has_no_answer(monkeypatch):
    monkeypatch.setattr(v, "classify_titles", lambda titles: {})
    ok, rejected = v.validate([_item()], "graphics_card", None)
    assert len(ok) == 1 and rejected == []


def test_llm_not_called_without_wanted_category(monkeypatch):
    def boom(titles):
        raise AssertionError("não devia chamar o LLM")
    monkeypatch.setattr(v, "classify_titles", boom)
    ok, _ = v.validate([_item()], None, None)
    assert len(ok) == 1