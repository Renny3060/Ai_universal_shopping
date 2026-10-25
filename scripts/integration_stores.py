"""Teste de integração das lojas.

Fase A: cada loja sozinha (sem cache, sem gravar), com tempo e erro, para ver quais falham ou são lentas.
Fase B: todas as lojas juntas, como numa pesquisa real, para ver se alguma atrasa ou bloqueia as outras.

Uso:
  python -m scripts.integration_stores                      termo por defeito: ssd 1tb
  python -m scripts.integration_stores "monitor 24"         outro termo
  python -m scripts.integration_stores --so-juntas          só a fase B
  python -m scripts.integration_stores --so-individual      só a fase A
  python -m scripts.integration_stores --vertical tech      só as lojas dessa vertical
Demora uns minutos (a fase A corre as lojas uma a uma)."""
import sys
import time
from collections import Counter

from rich.console import Console
from rich.table import Table

from backend.agents.group2_search.aggregator import NO_RESULTS, search_all
from backend.agents.group2_search.stores import STORES

console = Console()
SLOW_S = 60.0


def _verdict(n: int, err: str, secs: float) -> str:
    if err and err != NO_RESULTS:
        return "[red]ERRO[/red]"
    if n == 0:
        return "[yellow]sem itens[/yellow]"
    if secs > SLOW_S:
        return "[yellow]lenta[/yellow]"
    return "[green]ok[/green]"


def phase_a(term: str, names: list[str]) -> None:
    console.rule(f"Fase A: cada loja sozinha ({len(names)} lojas, termo: {term})")
    table = Table()
    for col in ("Loja", "Itens", "Segundos", "Estado", "Detalhe"):
        table.add_column(col)
    for name in names:
        t0 = time.monotonic()
        try:
            res, errs = search_all(term, stores=[name], save=False, use_cache=False, time_budget=120)
        except Exception as e:   # uma loja nunca deve parar o teste
            res, errs = [], {name: f"{type(e).__name__}: {e}"}
        secs = time.monotonic() - t0
        err = errs.get(name, "")
        table.add_row(name, str(len(res)), f"{secs:.0f}", _verdict(len(res), err, secs), err[:70])
        console.print(f"  {name}: {len(res)} itens em {secs:.0f}s {err[:60]}")
    console.print(table)


def phase_b(term: str, vertical: str | None) -> None:
    console.rule(f"Fase B: todas as lojas juntas (termo: {term})")
    t0 = time.monotonic()
    res, errs = search_all(term, save=False, use_cache=False, vertical=vertical)
    secs = time.monotonic() - t0
    by_store = Counter(r.store for r in res)
    table = Table()
    for col in ("Loja", "Itens", "Detalhe"):
        table.add_column(col)
    for name in STORES:
        if vertical and vertical not in STORES[name].get("verticals", []):
            continue
        table.add_row(name, str(by_store.get(name, 0)), errs.get(name, "")[:80])
    console.print(table)
    console.print(f"Total: {len(res)} itens em {secs:.0f}s | lojas com erro: "
                  f"{sum(1 for e in errs.values() if e != NO_RESULTS)} | sem resultados: "
                  f"{sum(1 for e in errs.values() if e == NO_RESULTS)}")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    vertical = None
    if "--vertical" in args:
        i = args.index("--vertical")
        vertical = args[i + 1]
        del args[i:i + 2]
    only_a = "--so-individual" in args
    only_b = "--so-juntas" in args
    args = [a for a in args if not a.startswith("--")]
    term = " ".join(args) or "ssd 1tb"
    names = [n for n in STORES if not vertical or vertical in STORES[n].get("verticals", [])]
    if not only_b:
        phase_a(term, names)
    if not only_a:
        phase_b(term, vertical)


if __name__ == "__main__":
    main()
