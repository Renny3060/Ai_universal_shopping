from typing import Optional

from backend.agents.group2_search.stores import STORES


def is_external_seller(store: str, seller_name: Optional[str], store_cfgs: Optional[dict] = None) -> bool:
    """True se a loja tem own_seller_names configurado e o vendedor não é um deles.
    Sem vendedor conhecido, ou numa loja sem own_seller_names, devolve False."""
    cfgs = STORES if store_cfgs is None else store_cfgs
    own = [n.lower() for n in cfgs.get(store, {}).get("own_seller_names", [])]
    return bool(own and seller_name and seller_name.strip().lower() not in own)