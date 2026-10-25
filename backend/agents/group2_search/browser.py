from typing import Optional

from playwright.sync_api import sync_playwright

from backend.agents.group2_search.anti_block import polite_delay, random_user_agent
from backend.config import DATA_DIR

DEBUG_DIR = DATA_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

# Espera até existir pelo menos um elemento com um número diferente de zero.
# Assim ignora cartões vazios (skeleton) e preços "0,00 €".
_WAIT_FOR_VALUE = """
sel => [...document.querySelectorAll(sel)].some(e => /[1-9]/.test(e.textContent))
"""


def fetch_html(url: str, wait_selector: Optional[str] = None,
               save_as: Optional[str] = None, timeout_ms: int = 30000,
               headless: bool = True) -> str:
    """Abre a página num Chromium real e devolve o HTML já renderizado."""
    polite_delay()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            user_agent=random_user_agent(),
            locale="pt-PT",
            timezone_id="Europe/Lisbon",
            viewport={"width": 1366, "height": 850},
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_selector:
                try:
                    page.wait_for_function(_WAIT_FOR_VALUE, arg=wait_selector, timeout=20000)
                except Exception:
                    pass
            else:
                page.wait_for_timeout(2500)

            # scroll suave para ativar carregamento preguiçoso (lazy loading)
            for _ in range(4):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(600)
            page.wait_for_timeout(800)

            html = page.content()
        finally:
            ctx.close()
            browser.close()

    if save_as:
        (DEBUG_DIR / save_as).write_text(html, encoding="utf-8")
    return html