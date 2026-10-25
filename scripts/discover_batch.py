"""Testa em lote as lojas candidatas (CSV do Gemini) com a mesma lógica do discover_store.

Para cada loja: abre a página inicial, aceita cookies, pesquisa um termo genérico da categoria,
lê o URL, deteta bloqueio e testa JSON-LD. Escreve data/lojas_resultado.csv (uma linha por loja)
e vai guardando à medida que avança, por isso podes interromper (Ctrl+C) e retomar com --resume.

Uso:
  python -m scripts.discover_batch [ficheiro.csv] [--limit N] [--resume] [--only nome] [--visible]
  python -m scripts.discover_batch [ficheiro.csv] --retry sem_termo_no_url   repete só as lojas com esse estado
Por defeito lê data/lojas_candidatas.csv.
"""
import csv
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from rich.console import Console

from backend.agents.group2_search.anti_block import random_user_agent
from backend.agents.group2_search.batch_discovery import (
    BLOCKED, NEEDS_CSS, NO_BOX, NO_TERM_IN_URL, OK_JSONLD, OPEN_ERROR,
    classify, drop_known, host_of, known_hosts_from_stores, read_candidates, term_for,
)
from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.discovery import store_entry, template_from_url
from backend.agents.group2_search.jsonld import extract_products
from backend.agents.group2_search.stores import STORES
from backend.config import DATA_DIR
from scripts.discover_store import accept_cookies, find_search_input, submit_search

console = Console()
RESULT_FILE = DATA_DIR / "lojas_resultado.csv"
FIELDS = ["nome", "url_inicial", "pais", "categoria", "termo", "estado", "n_produtos",
          "url_pesquisa", "modelo", "q_sep", "entrada_stores", "detalhe"]
PAUSE_BETWEEN_STORES = 4.0


def test_store(browser, row: dict) -> dict:
    home = row["url_inicial"]
    parts = urlsplit(home)
    base = f"{parts.scheme}://{parts.netloc}"
    term = term_for(row.get("categoria", ""), row.get("pais", "PT"))
    out = {k: "" for k in FIELDS}
    out.update(nome=row.get("nome", ""), url_inicial=home, pais=row.get("pais", ""),
               categoria=row.get("categoria", ""), termo=term, n_produtos=0)
    ctx = browser.new_context(user_agent=random_user_agent(), locale="pt-PT",
                              timezone_id="Europe/Lisbon", viewport={"width": 1366, "height": 850})
    page = ctx.new_page()
    opened = blocked = found_box = False
    template = q_sep = None
    final_url = html = ""
    n_products = 0
    try:
        try:
            page.goto(base, wait_until="domcontentloaded", timeout=30000)
            opened = True
        except Exception as e:
            out["detalhe"] = f"{type(e).__name__}: {str(e)[:120]}"
        if opened:
            page.wait_for_timeout(2500)
            accept_cookies(page)
            box, _sel = find_search_input(page)
            found_box = box is not None
            if found_box:
                start_url = page.url
                submit_search(page, box, term)
                try:
                    page.wait_for_url(lambda u: u != start_url, timeout=12000)
                except Exception:
                    pass
                page.wait_for_timeout(3500)
                for _ in range(3):
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(500)
                final_url = page.url
                html = page.content()
                reason = detect_block(html)
                blocked = bool(reason)
                if reason:
                    out["detalhe"] = reason
                found = template_from_url(final_url, term)
                if found:
                    template, q_sep = found
                    n_products = len(extract_products(html, base))
            else:
                html = page.content()
                reason = detect_block(html)
                if reason:
                    blocked = True
                    out["detalhe"] = reason
    except Exception as e:
        out["detalhe"] = f"{type(e).__name__}: {str(e)[:120]}"
    finally:
        ctx.close()

    out["estado"] = classify(opened=opened, blocked=blocked, found_box=found_box,
                             has_template=template is not None, n_products=n_products)
    out["n_produtos"] = n_products
    out["url_pesquisa"] = final_url
    if template:
        out["modelo"], out["q_sep"] = template, q_sep or ""
        if out["estado"] == OK_JSONLD:
            name = host_of(home).split(".")[0]
            out["entrada_stores"] = store_entry(name, final_url, template, q_sep).replace("\n", " ")
    if html and out["estado"] in (NEEDS_CSS, NO_TERM_IN_URL):
        debug = DATA_DIR / "debug" / f"discover_{host_of(home).split('.')[0]}.html"
        debug.parent.mkdir(exist_ok=True)
        debug.write_text(html, encoding="utf-8")
    return out


def load_done() -> set[str]:
    if not RESULT_FILE.exists():
        return set()
    with open(RESULT_FILE, newline="", encoding="utf-8-sig") as f:
        return {host_of(r["url_inicial"]) for r in csv.DictReader(f) if r.get("url_inicial")}


def load_rows() -> list[dict]:
    if not RESULT_FILE.exists():
        return []
    with open(RESULT_FILE, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("url_inicial")]


def save_rows(rows: list[dict]) -> None:
    with open(RESULT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def backup_results() -> None:
    if RESULT_FILE.exists():
        backup = RESULT_FILE.with_name(f"lojas_resultado_{datetime.now():%Y%m%d_%H%M%S}.csv")
        shutil.copy2(RESULT_FILE, backup)
        console.print(f"[yellow]Cópia do resultado anterior em {backup.name}[/yellow]")


def run_retry(rows: list[dict], by_host: dict[str, dict], visible: bool) -> None:
    """Repete as lojas dadas e substitui a linha de cada uma no ficheiro de resultados."""
    backup_results()
    console.print(f"{len(rows)} lojas a repetir (cerca de {len(rows) * 25 // 60 + 1} min).")
    counts: dict[str, int] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible)
        try:
            for i, row in enumerate(rows, 1):
                res = test_store(browser, row)
                by_host[host_of(row["url_inicial"])] = res
                save_rows(list(by_host.values()))
                counts[res["estado"]] = counts.get(res["estado"], 0) + 1
                color = {OK_JSONLD: "green", NEEDS_CSS: "yellow"}.get(res["estado"], "red")
                console.print(f"[{i}/{len(rows)}] {res['nome']}: [{color}]{res['estado']}[/{color}] "
                              f"({res['n_produtos']} produtos) {res['detalhe']}")
                time.sleep(PAUSE_BETWEEN_STORES)
        except KeyboardInterrupt:
            console.print("[yellow]Interrompido; o que já foi repetido ficou guardado.[/yellow]")
        finally:
            browser.close()
    console.print("\nResumo:", counts)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    only = None
    if "--only" in flags:
        only = flags[flags.index("--only") + 1].lower()
        args = [a for a in args if a.lower() != only]
    retry = None
    if "--retry" in flags:
        retry = flags[flags.index("--retry") + 1]
        args = [a for a in args if a != retry]
    limit = None
    if "--limit" in flags:
        limit = int(flags[flags.index("--limit") + 1])
        args = [a for a in args if a != str(limit)]
    src = Path(args[0]) if args else DATA_DIR / "lojas_candidatas.csv"
    if not src.exists():
        sys.exit(f"Não encontro {src}. Guarda o CSV do Gemini aí (UTF-8).")

    rows = drop_known(read_candidates(src), known_hosts_from_stores(STORES))
    if only:
        rows = [r for r in rows if only in r.get("nome", "").lower() or only in r["url_inicial"].lower()]
    if retry:
        by_host = {host_of(r["url_inicial"]): r for r in load_rows()}
        rows = [r for r in rows if by_host.get(host_of(r["url_inicial"]), {}).get("estado") == retry]
        if limit:
            rows = rows[:limit]
        run_retry(rows, by_host, "--visible" in flags)
        return
    if "--resume" in flags:
        done = load_done()
        rows = [r for r in rows if host_of(r["url_inicial"]) not in done]
    if limit:
        rows = rows[:limit]
    console.print(f"{len(rows)} lojas a testar (cerca de {len(rows) * 25 // 60 + 1} min).")

    RESULT_FILE.parent.mkdir(exist_ok=True)
    new_file = not RESULT_FILE.exists() or "--resume" not in flags
    if new_file:   # nunca apagar resultados anteriores sem cópia
        backup_results()
    counts: dict[str, int] = {}
    with open(RESULT_FILE, "w" if new_file else "a", newline="", encoding="utf-8-sig") as f, \
            sync_playwright() as p:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        browser = p.chromium.launch(headless="--visible" not in flags)
        try:
            for i, row in enumerate(rows, 1):
                res = test_store(browser, row)
                writer.writerow(res)
                f.flush()
                counts[res["estado"]] = counts.get(res["estado"], 0) + 1
                color = {OK_JSONLD: "green", NEEDS_CSS: "yellow"}.get(res["estado"], "red")
                console.print(f"[{i}/{len(rows)}] {res['nome']}: [{color}]{res['estado']}[/{color}] "
                              f"({res['n_produtos']} produtos) {res['detalhe']}")
                time.sleep(PAUSE_BETWEEN_STORES)
        except KeyboardInterrupt:
            console.print("[yellow]Interrompido. Retoma com --resume.[/yellow]")
        finally:
            browser.close()

    console.print("\nResumo:", counts)
    console.print(f"Resultados em {RESULT_FILE}")
    console.print("ok_jsonld = pronta (entrada em 'entrada_stores'); precisa_css = HTML em data\\debug\\.")


if __name__ == "__main__":
    main()