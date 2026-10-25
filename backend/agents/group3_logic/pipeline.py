from typing import Optional

from backend.agents.group2_search.stores import STORES
from backend.agents.group3_logic.categories import infer_wanted_category
from backend.agents.group3_logic.book_rules import mark_books
from backend.agents.group3_logic.dedupe import dedupe
from backend.agents.group3_logic.financial_agent import apply_costs
from backend.agents.group3_logic.outliers import split_outliers
from backend.agents.group1_input.request_parser import ParsedRequest
from backend.agents.group3_logic.relevance_rules import split_not_the_item
from backend.agents.group3_logic.request_filters import apply_request_filters, apply_soft_preferences
from backend.agents.group3_logic.scoring_agent import rank
from backend.agents.group3_logic.validator_agent import validate
from backend.agents.group3_logic.vertical_rules import split_non_vehicles
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct, RejectedProduct
from backend.schemas.search import ProductSpecs
from backend.services.url_safety import check_url


def run_group3(
    results: list[ProductResult],
    wanted_text: str = "",
    max_budget: Optional[float] = None,
    specs: Optional[ProductSpecs] = None,
    sort: str = "best_value",
    vertical: Optional[str] = None,
    min_price: Optional[float] = None,
    request: Optional[ParsedRequest] = None,
) -> tuple[list[RankedProduct], list[RejectedProduct], Optional[str]]:
    items = apply_costs(results, STORES)                    # Agente 13

    safe: list[RankedProduct] = []                          # Agente 14
    unsafe: list[RejectedProduct] = []
    for item in items:
        cfg = STORES.get(item.product.store, {})
        check = check_url(item.product.url, cfg.get("base_url"), cfg.get("extra_domains"))
        if check.ok:
            safe.append(item)
        else:
            unsafe.append(RejectedProduct(
                product=item.product,
                reason="URL suspeito: " + "; ".join(check.problems),
            ))

    # Brinquedos, miniaturas e acessórios "para <o artigo pedido>" saem antes do validador (poupa LLM).
    safe, not_item = split_not_the_item(safe, wanted_text, vertical)

    # O que o pedido diz (estado, marca, processador, orçamento mínimo), antes do validador (poupa LLM).
    from_request: list[RejectedProduct] = []
    if request:
        safe, from_request = apply_request_filters(safe, request)

    wanted = infer_wanted_category(wanted_text)
    ok, rejected = validate(safe, wanted, max_budget, specs)   # Agente 16
    ok = dedupe(ok)                                         # listagens repetidas
    ok, parts = split_non_vehicles(ok, wanted_text, vertical, STORES, min_price)   # peças e preço mínimo   # peças em cars/moto
    ok = mark_books(ok, wanted_text, STORES)                # livros depois dos restantes
    outliers: list[RejectedProduct] = []
    if wanted:                      # só com categoria conhecida (hardware); carros etc. variam demais
        ok, outliers = split_outliers(ok)
    penalties = {n: c["rank_penalty"] for n, c in STORES.items() if c.get("rank_penalty")} if wanted else None
    ranked = rank(ok, sort, penalties)                      # Agente 15
    if request:
        ranked = apply_soft_preferences(ranked, request, sort)
    return ranked, unsafe + not_item + from_request + rejected + parts + outliers, wanted