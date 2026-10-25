import re

from backend.schemas.ranking import RankedProduct


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower()).strip(" .")


def dedupe(items: list[RankedProduct]) -> list[RankedProduct]:
    """Junta artigos com a mesma loja, o mesmo título e o mesmo custo total.
    Mantém o primeiro e avisa quantas listagens iguais havia. Preserva a ordem."""
    groups: dict[tuple, list[RankedProduct]] = {}
    for item in items:
        key = (item.product.store, _norm(item.product.title), round(item.total_cost, 2))
        groups.setdefault(key, []).append(item)

    out: list[RankedProduct] = []
    for group in groups.values():
        first = group[0]
        if len(group) > 1:
            first.warnings.append(f"{len(group)} listagens iguais nesta loja (só se mostra 1).")
        out.append(first)
    return out