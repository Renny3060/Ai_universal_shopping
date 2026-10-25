"""Filtros que vêm do que o utilizador escreveu no pedido (estado, marca, processador, orçamento
mínimo) e bónus para as preferências ("de preferência preto / da Samsung").

Regra de ouro: só se rejeita quando o título CONTRARIA o pedido (outra marca, outro processador,
outro estado). Quando o título não diz nada, o artigo fica com um aviso.
"""
import re
from typing import Optional

from backend.agents.group1_input.request_parser import ParsedRequest, extract_cpu
from backend.agents.group3_logic.scoring_agent import _unconfirmed
from backend.schemas.ranking import RankedProduct, RejectedProduct
from backend.utils.brands import find_brands, fold

SOFT_BRAND_BONUS = 8.0
SOFT_EXTRA_BONUS = 4.0
MAX_BONUS = 12.0

_CONDITION_PT = {"new": "novo", "used": "usado", "refurbished": "recondicionado"}


def apply_request_filters(
    items: list[RankedProduct], req: ParsedRequest,
) -> tuple[list[RankedProduct], list[RejectedProduct]]:
    ok: list[RankedProduct] = []
    rejected: list[RejectedProduct] = []

    for item in items:
        p = item.product

        if req.min_budget and item.total_cost < req.min_budget:
            rejected.append(RejectedProduct(
                product=p, reason=f"abaixo do orçamento mínimo ({req.min_budget:g} €)"))
            continue

        if req.conditions and p.condition not in req.conditions:
            wanted = "/".join(_CONDITION_PT.get(c, c) for c in req.conditions)
            rejected.append(RejectedProduct(
                product=p,
                reason=f"estado diferente ({_CONDITION_PT.get(p.condition, p.condition)}; pedido: {wanted})"))
            continue

        if req.brands:
            found = set(find_brands(p.title))
            if found and not (found & set(req.brands)):
                rejected.append(RejectedProduct(
                    product=p,
                    reason=f"marca diferente ({', '.join(sorted(found))}; pedido: {' ou '.join(req.brands)})"))
                continue
            if not found:
                item.warnings.append(f"Marca não confirmada no título: {' ou '.join(req.brands)}")

        if req.cpu:
            cpu = extract_cpu(p.title)
            if cpu and cpu != req.cpu:
                rejected.append(RejectedProduct(
                    product=p, reason=f"processador diferente ({cpu}; pedido: {req.cpu})"))
                continue
            if not cpu:
                item.warnings.append(f"Processador não confirmado no título: {req.cpu}")

        ok.append(item)
    return ok, rejected


def _has_word(title_folded: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(fold(word))}(?![a-z0-9])", title_folded) is not None


def apply_soft_preferences(
    items: list[RankedProduct], req: ParsedRequest, sort: str = "best_value",
) -> list[RankedProduct]:
    """Soma um pequeno bónus (máx. 12 pontos) aos artigos que têm as preferências pedidas e volta a
    ordenar. Em 'cheapest' não mexe: a ordem é só o preço."""
    if sort == "cheapest" or not (req.soft_brands or req.extras):
        return items
    for item in items:
        t = fold(item.product.title)
        bonus = 0.0
        if req.soft_brands and set(find_brands(item.product.title)) & set(req.soft_brands):
            bonus += SOFT_BRAND_BONUS
        bonus += SOFT_EXTRA_BONUS * sum(1 for e in req.extras if _has_word(t, e))
        if bonus:
            item.score = round(min(100.0, item.score + min(bonus, MAX_BONUS)), 1)
    return sorted(items, key=lambda i: (_unconfirmed(i), -i.score))
