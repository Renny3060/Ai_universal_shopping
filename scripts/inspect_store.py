import re
import sys
from collections import Counter

from bs4 import BeautifulSoup

from backend.agents.group2_search.browser import fetch_html

if len(sys.argv) < 2:
    sys.exit('Uso: python -m scripts.inspect_store "URL_DA_PESQUISA"')

url = sys.argv[1]
html = fetch_html(url, save_as="inspect.html")
soup = BeautifulSoup(html, "lxml")

price_re = re.compile(r"\d+[.,]\d{2}\s*€|€\s*\d+[.,]\d{2}")
price_els = [e for e in soup.find_all(True) if e.string and price_re.search(e.string)]


def sig(el) -> str:
    cls = el.get("class") or []
    return el.name + ("." + ".".join(cls) if cls else "")


print(f"HTML: {len(html)} caracteres | elementos com preço: {len(price_els)}")
if len(price_els) == 0:
    print("Nenhum preço encontrado: a página pode ter bloqueado o acesso (CAPTCHA/cookies).")
    print("Vê o ficheiro data\\debug\\inspect.html")
    sys.exit()

print("\nElementos de preço (tag.classe -> quantidade):")
for s, n in Counter(sig(e) for e in price_els).most_common(6):
    print(f"  {n:3d}  {s}")

anc = Counter()
for e in price_els:
    for p in list(e.parents)[:6]:
        if p.name in ("body", "html", "[document]"):
            break
        anc[sig(p)] += 1
print("\nCandidatos a cartão de produto (ancestrais repetidos):")
for s, n in anc.most_common(8):
    print(f"  {n:3d}  {s}")

print("\nExemplo de preço:", price_els[0].get_text(strip=True))