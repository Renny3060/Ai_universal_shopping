import sys

from rich.console import Console
from rich.table import Table

from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES

if len(sys.argv) < 3 or sys.argv[1] not in STORES:
    sys.exit(f'Uso: python -m scripts.test_store <loja> "pesquisa"   (lojas: {", ".join(STORES)})')

store, termo = sys.argv[1], " ".join(sys.argv[2:])
scraper = ConfigurableScraper(store, STORES[store])
items = scraper.search(termo, use_cache=False, debug=True)

table = Table(title=f"{store}: {termo} ({len(items)} resultados)")
table.add_column("Preço", justify="right")
table.add_column("Título", overflow="fold")
for i in items[:15]:
    table.add_row(f"{i.price:.2f} €", i.title[:80])
Console().print(table)