import sys
import traceback

from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES
from backend.config import settings


def main() -> None:
    store = sys.argv[1] if len(sys.argv) > 1 else "worten"
    term = sys.argv[2] if len(sys.argv) > 2 else "rtx 5060 placa grafica"
    print("loja:", store, "| termo:", term, "| MAX_PAGES:", getattr(settings, "max_pages", "n/d"))
    scraper = ConfigurableScraper(store, STORES[store])
    try:
        items = scraper.search(term, use_cache=False, debug=True)
    except Exception:
        print("EXCEÇÃO no scraper:")
        traceback.print_exc()
        return
    print("itens devolvidos:", len(items))
    for it in items[:3]:
        print(" -", it.price, it.title[:70], "|", it.seller_name)


if __name__ == "__main__":
    main()