import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.table import Table

from backend.agents.group1_input.pipeline import LAST_RUN as G1_RUN, run_group1
from backend.agents.group1_input.request_parser import describe, finalize_request, parse_request
from backend.agents.group1_input.profile_agent import load_user_context
from backend.agents.group3_logic.categories import category_hint
from backend.agents.group3_logic.category_llm import LAST_RUN
from backend.agents.group3_logic.near_misses import MIN_RESULTS, near_misses
from backend.agents.group3_logic.pipeline import run_group3
from backend.utils.query_cleaning import clean_search_term
from backend.agents.group3_logic.vertical_rules import detect_vertical
from backend.agents.group2_search.aggregator import NO_RESULTS, search_all

console = Console()

vertical = None
if "--vertical" in sys.argv:
    vertical = sys.argv[sys.argv.index("--vertical") + 1]

min_price = None
if "--min-preco" in sys.argv:
    min_price = float(sys.argv[sys.argv.index("--min-preco") + 1])

skip = {v for v in (vertical, None if min_price is None else sys.argv[sys.argv.index("--min-preco") + 1]) if v}
args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in skip]
sort = "cheapest" if "--barato" in sys.argv else "best_value"
text = " ".join(args)
if vertical == "todas":
    vertical = None
elif vertical is None:
    vertical = detect_vertical(text)
if not text:
    sys.exit('Uso: python -m scripts.search_smart "RTX 5060 até 500€" [--barato] [--vertical tech]')

T0 = time.monotonic()
console.print("[yellow]A pesquisa pode demorar alguns minutos (máx. 10) para dar resultados de qualidade. Não feches.[/yellow]")
console.print("[dim]A interpretar o pedido (Grupo 1) e a pesquisar nas lojas ao mesmo tempo...[/dim]")
pool = ThreadPoolExecutor(max_workers=1)
g1_future = pool.submit(run_group1, text)          # LLM em paralelo com o scraping
req = parse_request(text)          # regras instantâneas: termo, orçamento, estado, marca, requisitos
term = req.term
eq = None
if req.needs_llm_term:  # pedido sem nome de artigo claro ou demasiado longo: o LLM resume-o
    eq = g1_future.result()
    term = clean_search_term(" ".join(eq.query.keywords[:3])) or term
hint = category_hint(term, text)
excluded = load_user_context().excluded_stores
console.print(f"[dim]Interpretação: {describe(req)}[/dim]")
console.print(f"Pesquisa: [bold]{term}[/bold] | dica de categoria: {hint or '-'} | vertical: {vertical or 'todas'}")

results, errors = search_all(term, excluded=excluded, hint=hint, vertical=vertical)
eq = eq or g1_future.result()
req, specs = finalize_request(req, eq)   # junta regras + LLM
pool.shutdown(wait=False)
T_G1 = time.monotonic()
if G1_RUN["llm_failed"]:
    console.print("[yellow]AVISO: Ollama indisponível; só o orçamento (se escrito) e as regras foram aplicados.[/yellow]")
console.print(f"Orçamento máx.: {req.max_budget}")
T_SCRAPE = time.monotonic()
ranked, rejected, wanted = run_group3(
    results, wanted_text=term, max_budget=req.max_budget, specs=specs, sort=sort,
    vertical=vertical, min_price=min_price, request=req,
)
T_G3 = time.monotonic()
if LAST_RUN["failed_titles"]:
    console.print(
        f"[yellow]AVISO: {LAST_RUN['failed_titles']} títulos sem classificação por LLM "
        f"(Ollama desligado?); usadas as regras.[/yellow]"
    )

table = Table(title=f"{len(ranked)} resultados (categoria: {wanted or 'qualquer'}, ordem: {sort})")
for col in ("Score", "Total", "Preço", "Impostos", "Loja", "Estado", "Título"):
    table.add_column(col, justify="right" if col in ("Score", "Total", "Preço", "Impostos") else "left",
                     overflow="fold")
for i in ranked[:15]:
    p = i.product
    table.add_row(f"{i.score:.0f}", f"{i.total_cost:.2f}", f"{p.price:.2f}", f"{i.taxes:.2f}",
                  p.store, p.condition, p.title[:60])
console.print(table)

if rejected:
    console.print("\nRejeitados:", dict(Counter(r.reason for r in rejected)))
if len(ranked) < MIN_RESULTS and rejected:
    close = near_misses(rejected, wanted, req.max_budget, min_budget=req.min_budget)
    if close:
        console.print("\n[cyan]Poucos resultados. Quase cumprem o pedido (só falham estado, marca ou mínimo):[/cyan]")
        for r in close:
            console.print(f"  {r.product.price:8.2f} € | {r.product.store:12} | {r.product.title[:55]} -> {r.reason}")
warns = Counter(w for i in ranked for w in i.warnings)
for w, n in warns.most_common(4):
    console.print(f"[yellow]Aviso ({n} produtos):[/yellow] {w}")
for loja, erro in errors.items():
    if erro == NO_RESULTS:
        console.print(f"[dim]Sem resultados em {loja}.[/dim]")
    else:
        console.print(f"[red]Erro em {loja}:[/red] {erro}")
if LAST_RUN.get("skipped_titles"):
    console.print(f"[yellow]AVISO: {LAST_RUN['skipped_titles']} títulos sem LLM por falta de tempo; usadas as regras.[/yellow]")
console.print(
    f"[dim]Tempo: Grupo 1 + lojas (em paralelo) {T_SCRAPE - T0:.0f}s | "
    f"Grupo 3 {T_G3 - T_SCRAPE:.0f}s | total {T_G3 - T0:.0f}s[/dim]"
)
