from typing import Optional

from backend.schemas.ranking import RankedProduct

CONDITION_FACTOR = {"new": 1.0, "refurbished": 0.75, "used": 0.3}
W_PRICE, W_CONDITION = 0.8, 0.2   # sem dados de vendedor/entrega ainda (Pilar 4)

# Aviso do validador quando há categoria pedida mas o título não permite confirmá-la (o LLM não teve
# tempo e as regras não o reconhecem). Estes itens passam sempre DEPOIS dos confirmados, qualquer
# que seja a ordenação: são mais prováveis de ser artigos de outra categoria (ex.: uma caixa de PC
# numa pesquisa de portáteis).
UNCONFIRMED_WARNING = "Categoria não identificada pelo título."

# Itens de lojas de livros quando o pedido não é sobre livros: também passam depois dos restantes.
BOOK_WARNING = "Livro (loja de livros): pode não ser o produto pedido."


def _unconfirmed(item: RankedProduct) -> bool:
    return UNCONFIRMED_WARNING in item.warnings or BOOK_WARNING in item.warnings


def rank(items: list[RankedProduct], sort: str = "best_value",
         penalties: Optional[dict[str, float]] = None) -> list[RankedProduct]:
    """sort: 'best_value' (pontuação) ou 'cheapest' (menor custo total).
    A pontuação é relativa aos resultados desta pesquisa (0 a 100).
    penalties: pontos a retirar à pontuação por loja (só em best_value); 'cheapest' ignora-as."""
    if not items:
        return items

    costs = [i.total_cost for i in items]
    lo, hi = min(costs), max(costs)
    for i in items:
        price_score = 1 - (i.total_cost - lo) / max(hi - lo, 0.2 * lo)
        cond = CONDITION_FACTOR.get(i.product.condition, 0.8)
        i.score = round(100 * (W_PRICE * price_score + W_CONDITION * cond), 1)
        if sort != "cheapest" and penalties:
            i.score = round(max(0.0, i.score - penalties.get(i.product.store, 0.0)), 1)

    if sort == "cheapest":
        return sorted(items, key=lambda i: (_unconfirmed(i), i.total_cost))
    return sorted(items, key=lambda i: (_unconfirmed(i), -i.score))