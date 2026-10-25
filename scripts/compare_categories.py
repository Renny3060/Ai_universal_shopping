import sys
from collections import Counter

# Evita crash ao redirecionar a saída (cp1252 não tem todos os caracteres dos títulos)
sys.stdout.reconfigure(errors="replace")

from backend.agents.group2_search.aggregator import search_all
from backend.agents.group3_logic.categories import category_hint, classify_title
from backend.agents.group3_logic.category_llm import classify_titles
from backend.utils.query_cleaning import clean_search_term

args = [a for a in sys.argv[1:] if not a.startswith("--")]
detalhe = "--detalhe" in sys.argv
text = " ".join(args) or "RTX 5060 até 600€"
term = clean_search_term(text)
results, errors = search_all(term, use_cache=True, hint=category_hint(term, text))
print(f"{len(results)} resultados para '{term}'  erros: {errors or 'nenhum'}")

llm = classify_titles([r.title for r in results])
pares = Counter()
for r in results:
    a, b = llm.get(r.title, "(sem resposta)"), str(classify_title(r.title))
    if a != b:
        pares[(a, b)] += 1
        if detalhe:
            print(f"LLM={a:<14} regex={b:<14} {r.store:<7} {r.title[:70]}")

print("\nCategorias segundo o LLM:")
for cat, n in Counter(llm.get(r.title, "(sem resposta)") for r in results).most_common():
    print(f"{n:>4}  {cat}")

print(f"\nDiscordâncias: {sum(pares.values())} de {len(results)}")
for (a, b), n in pares.most_common():
    print(f"{n:>4}  LLM={a:<14} regex={b}")