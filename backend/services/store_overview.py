"""Resumo das lojas disponíveis na aplicação (para a barra lateral): tipo, origem, estado e o que
devolveram na última pesquisa. Funções puras; a interface só desenha a tabela."""
from typing import Iterable, Optional

from backend.services import store_health

SOLO_LABEL = "solo"


def _last_search(store: str, counts: dict[str, int], errors: dict[str, str], no_results_msg: str) -> str:
    if store in errors:
        err = errors[store]
        return "sem resultados" if err == no_results_msg else f"erro: {str(err)[:60]}"
    if store in counts:
        return f"{counts[store]} itens"
    return "não pesquisada"


def store_overview(
    stores: dict,
    excluded: Iterable[str],
    last_counts: Optional[dict[str, int]] = None,
    last_errors: Optional[dict[str, str]] = None,
    no_results_msg: str = "",
    auto_keys: Optional[set[str]] = None,
    health: Optional[dict] = None,
) -> list[dict]:
    excluded = set(excluded)
    counts = last_counts or {}
    errors = last_errors or {}
    auto = store_health.auto_keys() if auto_keys is None else auto_keys
    hl = store_health.status() if health is None else health
    rows = []
    for name, cfg in stores.items():
        if name in excluded:
            state = "Excluída por ti"
        elif hl.get(name, {}).get("disabled"):
            state = "Desativada (falhas seguidas)"
        else:
            state = "Ativa"
        rows.append({
            "Loja": name,
            "Tipo": "/".join(cfg.get("verticals") or ["todas"]),
            "Origem": "automática" if name in auto else "manual",
            "Estado": state,
            "Última pesquisa": _last_search(name, counts, errors, no_results_msg),
        })
    return rows
