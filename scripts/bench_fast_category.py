"""Compara as regras rápidas com as categorias que o LLM já guardou na BD (cache v3 e v4).
Uso: python -m scripts.bench_fast_category"""
import collections
import json
import sqlite3

from backend.agents.group3_logic.fast_category import fast_classify
from backend.config import DATA_DIR
from backend.services.cache import make_key


def main() -> None:
    con = sqlite3.connect(str(DATA_DIR / "shopping.db"))
    cache = {k: p for k, p in con.execute("select cache_key, payload from search_cache where store='category'")}
    titles = [r[0] for r in con.execute("select distinct title from products")]
    labeled: dict[str, str] = {}
    for version in ("category-v3", "category-v4", "category-v5"):
        for t in titles:
            p = cache.get(make_key(version, t))
            if p:
                p = json.loads(p) if isinstance(p, str) else p
                if p.get("category") not in (None, "_skipped"):
                    labeled[t] = p["category"]
    hits = [(t, fast_classify(t), c) for t, c in labeled.items() if fast_classify(t)]
    diffs = [h for h in hits if h[1] != h[2]]
    print(f"títulos com categoria do LLM: {len(labeled)}")
    print(f"resolvidos pelas regras rápidas: {len(hits)} ({100 * len(hits) / max(1, len(labeled)):.0f}%)")
    print(f"diferentes do LLM: {len(diffs)}")
    print(collections.Counter(h[1] for h in hits))
    for t, f, c in diffs[:25]:
        print(f"  regras={f:14} llm={c:14} {t[:80]}")


if __name__ == "__main__":
    main()
