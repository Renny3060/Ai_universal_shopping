import re
import sys

from bs4 import BeautifulSoup

from backend.config import DATA_DIR

name = sys.argv[1] if len(sys.argv) > 1 else "inspect.html"
html = (DATA_DIR / "debug" / name).read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")

print("tamanho:", len(html))
print("titulo:", soup.title.get_text(strip=True) if soup.title else None)
print("simbolos €:", html.count("€"))
print("'RTX 5060' no HTML:", len(re.findall(r"rtx\s*5060", html, re.I)))

links = [a for a in soup.find_all("a", href=True) if "/produtos/" in a["href"]]
print("links /produtos/:", len(links), "| unicos:", len({a["href"] for a in links}))

print("\nScripts grandes ou com id (dados embutidos):")
for s in soup.find_all("script"):
    txt = s.string or ""
    if len(txt) > 20000 or s.get("type") == "application/ld+json" or s.get("id"):
        print(f"  id={s.get('id')} type={s.get('type')} tamanho={len(txt)} inicio={txt[:80]!r}")

for t in soup(["script", "style", "svg", "path"]):
    t.decompose()

if links:
    node = links[0]
    for _ in range(4):
        if node.parent:
            node = node.parent
    print("\nBloco à volta do 1º link de produto:")
    print(re.sub(r"\s+", " ", str(node))[:2500])
else:
    print("\nNenhum link de produto no HTML visível.")