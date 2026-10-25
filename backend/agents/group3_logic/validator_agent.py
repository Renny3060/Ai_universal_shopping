import os
from typing import Optional

from backend.agents.group3_logic.categories import classify_title
from backend.agents.group3_logic.fast_category import fast_classify
from backend.agents.group3_logic.category_llm import classify_titles
from backend.agents.group3_logic.scoring_agent import UNCONFIRMED_WARNING
from backend.agents.group3_logic.spec_check import check_numeric, is_numeric_requirement
from backend.schemas.ranking import RankedProduct, RejectedProduct
from backend.schemas.search import ProductSpecs


# Máximo de títulos enviados ao LLM por pesquisa (os mais baratos primeiro; os outros usam regras).
MAX_LLM_TITLES = int(os.environ.get("LLM_MAX_TITLES", "60"))   # LLM_MAX_TITLES=120 no ambiente para ser mais exaustivo


# Atributos que só repetem o próprio termo de pesquisa (já garantido por relevant()).
GENERIC_ATTRS = {"product_type", "product", "type", "category", "keywords", "keyword"}


def _is_noise(req) -> bool:
    """Requisito de texto que não acrescenta informação: atributo genérico ou atributo == valor."""
    attr = req.attribute.strip().lower().replace(" ", "_")
    if attr in GENERIC_ATTRS:
        return True
    return attr.replace("_", " ") == req.value.strip().lower()


def validate(
    items: list[RankedProduct],
    wanted_category: Optional[str],
    max_budget: Optional[float],
    specs: Optional[ProductSpecs] = None,
) -> tuple[list[RankedProduct], list[RejectedProduct]]:
    ok: list[RankedProduct] = []
    rejected: list[RejectedProduct] = []

    text_reqs = []
    numeric_reqs = []
    if specs:
        for req in specs.requirements:
            if not req.mandatory:
                continue
            if is_numeric_requirement(req):
                numeric_reqs.append(req)
                continue
            is_text = not req.value.replace(".", "").replace(",", "").isdigit()
            if req.operator in ("contains", "==") and is_text and not _is_noise(req):
                text_reqs.append(req)

    # Categorias pelo LLM (só quando há categoria pedida). Vem da cache se já classificado.
    # Só se gasta LLM nos itens que ainda podem ficar (dentro do orçamento), dos mais baratos
    # para os mais caros; os restantes usam as regras. Poupa a maior parte do tempo do LLM.
    llm_cats: dict[str, str] = {}
    fast_cats: dict[str, str] = {}
    if wanted_category:
        # 1.º regras rápidas e seguras (título começa por "Portátil", "SSD", "Memória RAM"...): sem LLM.
        for i in items:
            f = fast_classify(i.product.title)
            if f:
                fast_cats[i.product.title] = f
        candidates = [i for i in items
                      if not (max_budget and i.total_cost > max_budget)
                      and i.product.title not in fast_cats]
        candidates.sort(key=lambda i: i.total_cost)
        llm_cats = classify_titles([i.product.title for i in candidates[:MAX_LLM_TITLES]])

    for item in items:
        title = item.product.title
        llm_cat = llm_cats.get(title)
        fast_cat = fast_cats.get(title)
        item.category = fast_cat or llm_cat or classify_title(title)   # fallback: regras antigas
        via = ", via LLM" if (llm_cat and not fast_cat) else ""

        if wanted_category:
            if item.category and item.category != wanted_category:
                rejected.append(RejectedProduct(
                    product=item.product,
                    reason=f"categoria diferente ({item.category}{via})"))
                continue
            if item.category is None:
                item.warnings.append(UNCONFIRMED_WARNING)

        if max_budget and item.total_cost > max_budget:
            rejected.append(RejectedProduct(product=item.product, reason="acima do orçamento"))
            continue

        failed = None
        for req in numeric_reqs:
            res = check_numeric(title, req)
            if res is None:
                continue
            if res.status == "fail":
                failed = res
                break
            if res.status == "unknown":
                item.warnings.append(
                    f"Não confirmado no título: {res.attribute} {res.operator} {req.value}")
        if failed:
            rejected.append(RejectedProduct(
                product=item.product,
                reason=(f"não cumpre requisito: {failed.attribute} {failed.found:g} "
                        f"(pedido {failed.operator} {failed.wanted:g})"),
            ))
            continue

        for req in text_reqs:
            if req.value.lower() not in title.lower():
                item.warnings.append(f"Não confirmado no título: {req.attribute} {req.value}")

        ok.append(item)
    return ok, rejected