"""Descobre sozinho como pesquisar numa loja, a partir do endereço da página inicial.

Abre a loja, aceita cookies (se encontrar o botão), escreve o termo na caixa de pesquisa,
submete e lê o URL a que chegou. Depois testa JSON-LD e, se não servir, dá pistas de CSS
e guarda o HTML em data/debug/ para analisar.

Uso:
  python -m scripts.discover_store "https://www.loja.pt/" ["termo"] [--visible]
"""
import re
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from rich.console import Console

from backend.agents.group2_search.anti_block import random_user_agent
from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.discovery import (
    price_card_candidates, store_entry, template_from_url,
)
from backend.agents.group2_search.jsonld import extract_products
from backend.config import DATA_DIR

console = Console()

SEARCH_INPUTS = [
    'input[type="search"]',
    'input[name="q"]', 'input[name="query"]', 'input[name="search"]', 'input[name="s"]',
    'input[name="keyword"]', 'input[name="keywords"]', 'input[name="text"]',
    'input[placeholder*="esquis" i]', 'input[placeholder*="earch" i]',
    'input[placeholder*="rocur" i]', 'input[placeholder*="uscar" i]',
    'input[aria-label*="esquis" i]', 'input[aria-label*="earch" i]',
    'form[role="search"] input[type="text"]', '[role="search"] input',
]
COOKIE_TEXTS = [
    "Aceitar todos", "Aceitar tudo", "Aceitar e fechar", "Aceitar", "Aceito", "Concordo",
    "Permitir todos", "Accept all", "Accept", "Aceptar todo", "Aceptar",
]


def accept_cookies(page) -> None:
    for text in COOKIE_TEXTS:
        try:
            loc = page.get_by_role("button", name=re.compile(rf"^\s*{re.escape(text)}", re.I))
            if loc.count():
                loc.first.click(timeout=2500)
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def find_search_input(page):
    for sel in SEARCH_INPUTS:
        try:
            for el in page.locator(sel).all():
                if el.is_visible():
                    return el, sel
        except Exception:
            continue
    return None, None


def submit_search(page, box, term: str) -> None:
    """Escreve o termo na caixa e submete. Tolera banners e sobreposições que impedem o clique
    (causa dos 'Locator.click: Timeout'): tenta clique normal, depois forçado, depois foco por JS;
    se o Enter não mudar a página, submete o formulário."""
    try:
        box.click(timeout=4000)
    except Exception:
        try:
            page.keyboard.press("Escape")
            box.click(force=True, timeout=3000)
        except Exception:
            try:
                box.evaluate("el => el.focus()")
            except Exception:
                pass
    try:
        box.fill(term, timeout=4000)
    except Exception:
        box.evaluate(
            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", term)
    before = page.url
    try:
        box.press("Enter", timeout=4000)
    except Exception:
        pass
    page.wait_for_timeout(1500)
    if page.url == before:
        try:
            box.evaluate("el => { const f = el.form; if (f) { f.requestSubmit ? f.requestSubmit() : f.submit(); } }")
        except Exception:
            pass


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    home = args[0]
    term = args[1] if len(args) > 1 else "rtx 5060"
    visible = "--visible" in sys.argv
    parts = urlsplit(home)
    base = f"{parts.scheme}://{parts.netloc}"
    host = parts.netloc.replace("www.", "").split(".")[0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible)
        ctx = browser.new_context(
            user_agent=random_user_agent(), locale="pt-PT",
            timezone_id="Europe/Lisbon", viewport={"width": 1366, "height": 850},
        )
        page = ctx.new_page()
        try:
            console.print(f"[dim]A abrir {base} ...[/dim]")
            page.goto(base, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            accept_cookies(page)

            box, sel = find_search_input(page)
            if box is None:
                console.print("[red]Não encontrei a caixa de pesquisa.[/red] "
                              "Corre com --visible, ou cola-me o URL de uma pesquisa feita à mão.")
                return
            console.print(f"Caixa de pesquisa: [bold]{sel}[/bold]; a pesquisar '{term}' ...")
            start_url = page.url
            submit_search(page, box, term)
            try:
                page.wait_for_url(lambda u: u != start_url, timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(3500)
            for _ in range(4):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(600)
            page.wait_for_timeout(800)
            final_url = page.url
            html = page.content()
            page_links = [
                (a.get_attribute("href"), (a.inner_text() or "").strip())
                for a in page.locator("a[href]").all()[:400]
            ]
        finally:
            ctx.close()
            browser.close()

    debug_file = DATA_DIR / "debug" / f"discover_{host}.html"
    debug_file.parent.mkdir(exist_ok=True)
    debug_file.write_text(html, encoding="utf-8")

    console.print(f"\nURL da pesquisa: [cyan]{final_url}[/cyan]")
    reason = detect_block(html)
    if reason:
        console.print(f"[red]Possível bloqueio:[/red] {reason}")

    found = template_from_url(final_url, term)
    if not found:
        console.print("[yellow]Não consegui encontrar o termo no URL (pesquisa por POST ou por JavaScript).[/yellow]")
        console.print(f"HTML guardado em {debug_file}")
        return
    template, q_sep = found
    console.print(f"Modelo: [bold]{template}[/bold]  (q_sep: {q_sep or 'por defeito'})")

    pages = [h for h, t in page_links if h and t == "2"]
    if pages:
        console.print(f"Link da página 2 (para page_url, trocando o termo por {{q}} e o 2 por {{page}}): {pages[0]}")

    products = extract_products(html, base)
    console.print(f"Produtos no JSON-LD: [bold]{len(products)}[/bold]  | HTML: {len(html):,} caracteres")
    if products:
        for pr in products[:5]:
            console.print(f"  {pr['price']:.2f} {pr['currency']}  {pr['title'][:70]}")
        console.print("[green]Serve por JSON-LD. Cola em STORES (stores.py):[/green]")
        console.print(store_entry(host, final_url, template, q_sep), markup=False)
    else:
        console.print("[yellow]Sem JSON-LD. Pistas de cartão (assinatura, repetições; são só pistas):[/yellow]")
        for sig, n in price_card_candidates(html):
            console.print(f"  {n:4d}  {sig}", markup=False)
        console.print(f"HTML guardado em {debug_file}: anexa-o no chat para tirar os seletores.")


if __name__ == "__main__":
    main()