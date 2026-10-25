"""Quando um pedido detalhado dá poucos ou nenhuns resultados, mostra os artigos que só falharam
por critérios 'moles' do pedido (estado, marca, orçamento mínimo), para o utilizador perceber o
que relaxar. O orçamento máximo continua a ser duro."""
from typing import Optional

from backend.agents.group3_logic.categories import classify_title
from backend.agents.group3_logic.fast_category import fast_classify
from backend.schemas.ranking import RejectedProduct

SOFT_PREFIXES = ("estado diferente", "marca diferente", "abaixo do orçamento mínimo")
MIN_RESULTS = 3


def near_misses(
    rejected: list[RejectedProduct],
    wanted: Optional[str],
    max_budget: Optional[float] = None,
    limit: int = 8,
    min_budget: Optional[float] = None,
) -> list[RejectedProduct]:
    out: list[RejectedProduct] = []
    seen: set[str] = set()
    for r in rejected:
        if not r.reason.startswith(SOFT_PREFIXES):
            continue
        p = r.product
        if max_budget and p.price > max_budget:
            continue
        if wanted:
            cat = fast_classify(p.title) or classify_title(p.title)
            if cat is not None and cat != wanted:
                continue
        key = p.url or p.title
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    def distance(r: RejectedProduct) -> float:
        price = r.product.price
        if min_budget and price < min_budget:
            return min_budget - price
        if max_budget and price > max_budget:
            return price - max_budget
        return 0.0

    out.sort(key=lambda r: (distance(r), r.product.price))
    return out[:limit]
