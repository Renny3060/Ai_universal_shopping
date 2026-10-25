from statistics import median

from backend.schemas.ranking import RankedProduct, RejectedProduct

MIN_ITEMS = 8     # com menos resultados a mediana não é fiável: não filtra
RATIO = 0.35      # abaixo de 35% da mediana do custo total = atípico


def split_outliers(
    items: list[RankedProduct], ratio: float = RATIO, min_items: int = MIN_ITEMS,
) -> tuple[list[RankedProduct], list[RejectedProduct]]:
    """Separa itens com custo total muito abaixo da mediana (peças, ferramentas, anúncios enganadores)."""
    if len(items) < min_items:
        return items, []
    med = median(i.total_cost for i in items)
    if med <= 0:
        return items, []
    limit = med * ratio
    ok: list[RankedProduct] = []
    rejected: list[RejectedProduct] = []
    for i in items:
        if i.total_cost < limit:
            rejected.append(RejectedProduct(
                product=i.product,
                reason=f"preço atípico ({i.total_cost:.2f} € é menos de {ratio:.0%} da mediana, {med:.2f} €)",
            ))
        else:
            ok.append(i)
    return ok, rejected