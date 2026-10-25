import sys
from pathlib import Path

from bs4 import BeautifulSoup

from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES
from backend.config import DATA_DIR


def main() -> None:
    store = sys.argv[1] if len(sys.argv) > 1 else "worten"
    fname = sys.argv[2] if len(sys.argv) > 2 else "worten_diag.html"
    path = Path(DATA_DIR) / "debug" / fname
    html = path.read_text(encoding="utf-8", errors="replace")
    cfg = STORES[store]

    print("ficheiro:", path, len(html), "caracteres")
    print("bloqueio:", detect_block(html))
    print("config.card:", cfg.get("card"))
    print("config.wait:", cfg.get("wait"))

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(cfg["card"])
    print("cartões encontrados:", len(cards))
    if cards:
        print("atributos do 1.º cartão:", {k: str(v)[:60] for k, v in cards[0].attrs.items()})

    items = ConfigurableScraper(store, cfg).parse(html)
    print("itens após parse:", len(items))
    for it in items[:3]:
        print(" -", it.price, it.title[:70], "|", it.seller_name)


if __name__ == "__main__":
    main()