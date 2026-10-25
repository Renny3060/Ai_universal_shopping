"""Promove as lojas que passaram no teste ao vivo para data/stores_auto.json.

O stores.py carrega esse ficheiro no arranque (sem substituir lojas escritas à mão), por isso uma
loja promovida passa a ser pesquisada sem editar código.

Uso:
  python -m scripts.promote_generated                  promove as lojas com estado 'ok'
  python -m scripts.promote_generated --incluir-poucos também as que devolveram 1 a 4 itens
  python -m scripts.promote_generated --remover chave  tira uma loja do registo
  python -m scripts.promote_generated --listar         mostra o registo atual
"""
import csv
import importlib.util
import json
import sys

from rich.console import Console

from backend.agents.group2_search.auto_selectors import merge_stores
from backend.config import DATA_DIR

console = Console()
GEN_FILE = DATA_DIR / "stores_generated.py"
LIVE_FILE = DATA_DIR / "generated_live.csv"
REGISTRY = DATA_DIR / "stores_auto.json"


def load_registry() -> dict:
    if not REGISTRY.exists():
        return {}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(data: dict) -> None:
    REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_generated() -> dict:
    spec = importlib.util.spec_from_file_location("stores_generated", GEN_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AUTO_STORES


def main() -> None:
    registry = load_registry()
    if "--listar" in sys.argv:
        for key, cfg in registry.items():
            console.print(f"{key}: {cfg.get('base_url')} {cfg.get('verticals')}")
        console.print(f"{len(registry)} lojas no registo.")
        return
    if "--remover" in sys.argv:
        key = sys.argv[sys.argv.index("--remover") + 1]
        if registry.pop(key, None) is None:
            console.print(f"[yellow]{key} não está no registo.[/yellow]")
        else:
            save_registry(registry)
            console.print(f"{key} removida.")
        return
    if not (GEN_FILE.exists() and LIVE_FILE.exists()):
        console.print("[red]Faltam data/stores_generated.py e data/generated_live.csv "
                      "(corre scripts.auto_selectors e scripts.test_generated).[/red]")
        return
    accepted = {"ok", "poucos"} if "--incluir-poucos" in sys.argv else {"ok"}
    with open(LIVE_FILE, newline="", encoding="utf-8-sig") as f:
        keys = [r["chave"] for r in csv.DictReader(f) if r["estado"] in accepted]
    merged, added, skipped = merge_stores(registry, load_generated(), keys)
    save_registry(merged)
    console.print(f"Adicionadas ({len(added)}): {', '.join(added) or '-'}")
    if skipped:
        console.print(f"Ignoradas ({len(skipped)}, já existiam): {', '.join(skipped)}")
    console.print(f"Registo: {REGISTRY} ({len(merged)} lojas)")


if __name__ == "__main__":
    main()
