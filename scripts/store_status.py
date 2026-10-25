"""Estado de saúde das lojas do registo automático.

Uso:
  python -m scripts.store_status                   tabela com todas as lojas acompanhadas
  python -m scripts.store_status --reativar chave  volta a ativar uma loja desativada
"""
import sys

from rich.console import Console
from rich.table import Table

from backend.services.store_health import DISABLE_AFTER, auto_keys, reenable, status

console = Console()


def main() -> None:
    if "--reativar" in sys.argv:
        key = sys.argv[sys.argv.index("--reativar") + 1]
        console.print(f"{key} reativada." if reenable(key) else f"[yellow]{key} não tem histórico.[/yellow]")
        return
    data = status()
    table = Table()
    for col in ("Loja", "Estado", "Pesquisas", "Com itens", "Falhas seguidas", "Últimos itens", "Último ok", "Detalhe"):
        table.add_column(col)
    for key in sorted(auto_keys() | set(data)):
        s = data.get(key)
        if not s:
            table.add_row(key, "sem histórico", "0", "0", "0", "-", "-", "")
            continue
        estado = "[red]desativada[/red]" if s["disabled"] else "ativa"
        table.add_row(key, estado, str(s["runs"]), str(s["ok_runs"]), f"{s['streak']}/{DISABLE_AFTER}",
                      str(s["last_items"]), s["last_ok"][:16] or "-", s["last_detail"][:40])
    console.print(table)


if __name__ == "__main__":
    main()
