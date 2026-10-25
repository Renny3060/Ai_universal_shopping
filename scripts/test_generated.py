"""Testa AO VIVO as lojas de data/stores_generated.py com o ConfigurableScraper real.

Para cada loja pesquisa o termo de teste (1 página, sem cache) e regista quantos itens vieram,
quantos têm preço e um exemplo. Escreve data/generated_live.csv.
Estados: ok (itens plausíveis), suspeita (itens, mas o teste de plausibilidade falhou: ver detalhe),
poucos, vazio, erro. O promote_generated só promove as 'ok'. Vê sempre a coluna Exemplo: o teste
não prova que o preço está certo.

Uso: python -m scripts.test_generated [--only nome] [--visible]
"""
import csv
import importlib.util
import sys
import time

from rich.console import Console
from rich.table import Table

from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.plausibility import check_plausibility
from backend.config import DATA_DIR

console = Console()
GEN_FILE = DATA_DIR / "stores_generated.py"
OUT_CSV = DATA_DIR / "generated_live.csv"
PAUSE = 4.0
MIN_OK = 5


def load_generated():
    spec = importlib.util.spec_from_file_location("stores_generated", GEN_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AUTO_STORES, mod.AUTO_TERMS


def main() -> None:
    if not GEN_FILE.exists():
        console.print("[red]Falta data/stores_generated.py: corre primeiro scripts.auto_selectors[/red]")
        return
    only = sys.argv[sys.argv.index("--only") + 1].lower() if "--only" in sys.argv else None
    stores, terms = load_generated()
    rows = []
    for key, cfg in stores.items():
        if only and only not in key:
            continue
        term = terms.get(key, "ssd 1tb")
        console.print(f"[bold]{key}[/bold]: a pesquisar '{term}' ...")
        line = {"chave": key, "termo": term, "estado": "", "itens": 0, "exemplo": "", "detalhe": ""}
        try:
            scraper = ConfigurableScraper(key, cfg)
            items = scraper.search(term, use_cache=False, max_pages=1)
            line["itens"] = len(items)
            if items:
                line["exemplo"] = " || ".join(f"{x.price} | {x.title[:40]}" for x in items[:3])
                plausible, reasons = check_plausibility(
                    items, cfg["base_url"], cfg.get("extra_domains"), min_items=MIN_OK)
                if plausible:
                    line["estado"] = "ok"
                elif len(items) < MIN_OK:
                    line["estado"] = "poucos"
                else:
                    line["estado"] = "suspeita"
                    line["detalhe"] = "; ".join(reasons)
            else:
                line["estado"] = "vazio"
        except Exception as e:  # bloqueio, timeout, etc.
            line["estado"] = "erro"
            line["detalhe"] = f"{type(e).__name__}: {str(e)[:100]}"
        rows.append(line)
        time.sleep(PAUSE)

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["chave", "termo", "estado", "itens", "exemplo", "detalhe"])
        w.writeheader()
        w.writerows(rows)
    table = Table()
    for col in ("Loja", "Estado", "Itens", "Exemplo"):
        table.add_column(col)
    for r in rows:
        table.add_row(r["chave"], r["estado"], str(r["itens"]), (r["detalhe"] or r["exemplo"])[:70])
    console.print(table)
    console.print(f"{sum(1 for r in rows if r['estado'] == 'ok')} de {len(rows)} lojas ok. Relatório: {OUT_CSV}")


if __name__ == "__main__":
    main()
