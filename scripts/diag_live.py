import sys
from urllib.parse import quote_plus

from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.browser import fetch_html
from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES


def main() -> None:
    store = sys.argv[1] if len(sys.argv) > 1 else "worten"
    term = sys.argv[2] if len(sys.argv) > 2 else "rtx 5060 placa grafica"
    cfg = STORES[store]
    url = cfg["search_url"].format(q=quote_plus(term))
    print("URL:", url)
    print("wait:", cfg.get("wait"))

    for headless in (True, False):
        print(f"\n--- headless={headless} ---")
        try:
            html = fetch_html(
                url, wait_selector=cfg.get("wait"),
                save_as=f"{store}_live_{headless}.html", headless=headless,
            )
        except Exception as e:
            print("ERRO no fetch:", type(e).__name__, str(e)[:200])
            continue
        print("caracteres:", len(html))
        print("bloqueio:", detect_block(html))
        try:
            items = ConfigurableScraper(store, cfg).parse(html)
            print("itens após parse:", len(items))
        except Exception as e:
            print("ERRO no parse:", type(e).__name__, str(e)[:200])


if __name__ == "__main__":
    main()