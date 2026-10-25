"""Gera entradas para stores.py a partir dos HTML guardados pelo discover_batch.

Para cada loja 'precisa_css' em data/lojas_resultado.csv (com URL de pesquisa conhecido) lê
data/debug/discover_<loja>.html, propõe card/title/price/link e mede a cobertura.

Escreve:
  data/stores_generated.py        AUTO_STORES (entradas) e AUTO_TERMS (termo de teste por loja)
  data/auto_selectors_report.csv  uma linha por loja: estado, cartões, seletores, avisos, amostra

Nada vai para o stores.py sozinho: depois corre `python -m scripts.test_generated` (ao vivo) e
cola no stores.py só as que passarem.

Uso: python -m scripts.auto_selectors [--only nome]
"""
import csv
import json
import sys
from urllib.parse import urlsplit

from rich.console import Console
from rich.table import Table

from backend.agents.group2_search.auto_selectors import (
    entry_text, is_euro_country, page_hint, propose, store_slug, term_in_html, vertical_for,
)
from backend.agents.group2_search.batch_discovery import (
    NEEDS_CSS, category_key, host_of, known_hosts_from_stores, read_candidates, term_for,
)
from backend.agents.group2_search.stores import STORES
from backend.config import DATA_DIR

console = Console()
RESULT_FILE = DATA_DIR / "lojas_resultado.csv"
CANDIDATES_FILE = DATA_DIR / "lojas_candidatas.csv"
OUT_PY = DATA_DIR / "stores_generated.py"
OUT_CSV = DATA_DIR / "auto_selectors_report.csv"
FIELDS = ["nome", "chave", "estado", "n_cartoes", "card", "title", "price", "link",
          "avisos", "pagina2_href", "amostra"]


def main() -> None:
    only = sys.argv[sys.argv.index("--only") + 1].lower() if "--only" in sys.argv else None
    if not RESULT_FILE.exists():
        console.print(f"[red]Não encontrei {RESULT_FILE}. Corre primeiro o discover_batch.[/red]")
        return
    with open(RESULT_FILE, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("estado") == NEEDS_CSS]
    known = known_hosts_from_stores(STORES)
    types_by_host = {}
    if CANDIDATES_FILE.exists():   # o 'tipo' (loja própria, marketplace, classificados) vem do CSV de candidatas
        types_by_host = {host_of(c["url_inicial"]): (c.get("tipo") or "") for c in read_candidates(CANDIDATES_FILE)}
    generated: dict[str, dict] = {}
    terms: dict[str, str] = {}
    report: list[dict] = []

    for r in rows:
        if only and only not in r["nome"].lower():
            continue
        host = host_of(r["url_inicial"])
        if host in known:
            continue
        key = store_slug(r["nome"])
        debug = DATA_DIR / "debug" / f"discover_{host.split('.')[0]}.html"
        line = {k: "" for k in FIELDS} | {"nome": r["nome"], "chave": key}
        if not is_euro_country(r["pais"]):
            line["estado"] = "moeda_nao_euro"
        elif not r.get("modelo"):
            line["estado"] = "sem_url_pesquisa"
        elif not debug.exists():
            line["estado"] = "sem_html"
        else:
            html = debug.read_text(encoding="utf-8", errors="ignore")
            p = propose(html)
            if not p:
                line["estado"] = "sem_cartoes"
            else:
                term = r.get("termo") or term_for(r["categoria"], r["pais"])
                flags = list(p["flags"])
                if not term_in_html(html, term):
                    flags.append("o HTML guardado pode não ser a página de resultados")
                parts = urlsplit(r["url_inicial"])
                cfg = {
                    "search_url": r["modelo"],
                    "base_url": f"{parts.scheme}://{parts.netloc}",
                    "card": p["card"], "title": p["title"], "price": p["price"], "link": p["link"],
                    "country": (r["pais"] or "PT").upper(),
                    "currency": "EUR",
                    "verticals": vertical_for(category_key(r["categoria"])),
                }
                if r.get("q_sep"):
                    cfg["q_sep"] = r["q_sep"]
                if types_by_host.get(host, "").strip().lower() == "classificados":
                    # anúncios de particulares (como a OLX): usados, sem garantia, vários tipos de produto
                    cfg["verticals"] = ["tech", "general", "cars", "moto"]
                    cfg["default_condition"] = "used"
                    cfg["private_listings"] = True
                generated[key] = cfg
                terms[key] = term
                line |= {
                    "estado": "pronta" if not flags else "rever", "n_cartoes": p["n_cards"],
                    "card": p["card"], "title": p["title"], "price": p["price"], "link": p["link"],
                    "avisos": "; ".join(flags), "pagina2_href": page_hint(html) or "",
                    "amostra": " | ".join(f"{t} = {pr}" for t, pr, _ in p["samples"]),
                }
        report.append(line)

    body = ['"""Gerado por scripts.auto_selectors. Não editar à mão."""', "", "AUTO_STORES = {"]
    body += [entry_text(k, c) for k, c in generated.items()]
    body += ["}", "", "AUTO_TERMS = " + json.dumps(terms, ensure_ascii=False, indent=4), ""]
    OUT_PY.write_text("\n".join(body), encoding="utf-8")
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(report)

    table = Table(show_lines=False)
    for col in ("Loja", "Estado", "Cartões", "Avisos"):
        table.add_column(col)
    for line in report:
        table.add_row(line["nome"], line["estado"], str(line["n_cartoes"]), line["avisos"][:60])
    console.print(table)
    n_ok = sum(1 for x in report if x["estado"] in ("pronta", "rever"))
    console.print(f"{n_ok} de {len(report)} lojas com seletores propostos.")
    console.print(f"Entradas: {OUT_PY}\nRelatório: {OUT_CSV}")
    console.print("Próximo passo: python -m scripts.test_generated")


if __name__ == "__main__":
    main()
