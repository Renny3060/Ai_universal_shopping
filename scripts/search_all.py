import sys

from rich.console import Console
from rich.table import Table

from backend.agents.group1_input.profile_agent import load_user_context
from backend.agents.group2_search.aggregator import search_all

keywords = " ".join(sys.argv[1:])
if not keywords:
    sys.exit('Uso: python -m scripts.search_all "rtx 4060"')

user = load_user_context()
results, errors = search_all(keywords, excluded=user.excluded_stores)

table = Table(title=f"{keywords}: {len(results)} resultados")
table.add_column("Preço", justify="right")
table.add_column("Loja")
table.add_column("Estado")
table.add_column("Título", overflow="fold")
for r in results[:20]:
    table.add_row(f"{r.price:.2f} €", r.store, r.condition, r.title[:70])

console = Console()
console.print(table)
for loja, erro in errors.items():
    console.print(f"[red]Erro em {loja}:[/red] {erro}")