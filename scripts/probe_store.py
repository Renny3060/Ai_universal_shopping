"""Testa se uma loja nova se lê sem seletores CSS (JSON-LD / schema.org).

Uso:
  python -m scripts.probe_store "https://loja.pt/search?query=rtx+5060"
  python -m scripts.probe_store --file data\\debug\\worten.html
"""
import sys
from pathlib import Path
from urllib.parse import urlsplit

from rich.console import Console
from rich.table import Table

from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.browser import fetch_html
from backend.agents.group2_search.jsonld import JSONLD_SELECTOR, extract_products

console = Console()
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)

if args[0] == "--file":
    html = Path(args[1]).read_text(encoding="utf-8", errors="replace")
    base = ""
else:
    url = args[0]
    parts = urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    console.print(f"[dim]A abrir {url} ...[/dim]")
    html = fetch_html(url, wait_selector=JSONLD_SELECTOR, save_as="probe.html")

block = detect_block(html)
if block:
    console.print(f"[red]Possível bloqueio:[/red] {block}")

products = extract_products(html, base)
console.print(f"HTML: {len(html):,} caracteres | produtos no JSON-LD: [bold]{len(products)}[/bold]")

if products:
    table = Table(title="Primeiros produtos")
    for col in ("Preço", "Moeda", "Stock", "Título"):
        table.add_column(col, overflow="fold")
    for p in products[:8]:
        table.add_row(f"{p['price']:.2f}", p["currency"], "sim" if p["in_stock"] else "não", p["title"][:70])
    console.print(table)
    console.print("[green]Serve: basta search_url e base_url em stores.py (sem 'card').[/green]")
else:
    console.print("[yellow]Sem produtos no JSON-LD. Esta loja precisa de seletores CSS "
                  "(python -m scripts.inspect_store URL).[/yellow]")