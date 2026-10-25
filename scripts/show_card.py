import sys

from bs4 import BeautifulSoup

from backend.config import DATA_DIR

sel = sys.argv[1] if len(sys.argv) > 1 else "div.product-list div.bg-background-off"
soup = BeautifulSoup((DATA_DIR / "debug" / "inspect.html").read_text(encoding="utf-8"), "lxml")
cards = soup.select(sel)
print(len(cards), "cartões com", sel)

for card in cards[:2]:
    for t in card.find_all(["svg", "script", "style", "path"]):
        t.decompose()
    for t in card.find_all(True):
        t["class"] = [c for c in (t.get("class") or []) if len(c) < 25 and ":" not in c and "[" not in c][:4]
        for attr in ("srcset", "sizes", "style", "loading", "decoding"):
            t.attrs.pop(attr, None)
    print("-" * 60)
    print(str(card)[:3500])