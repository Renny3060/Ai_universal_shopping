"""Aplica, de forma idempotente, as correções pendentes de 17/10/2026:

1. categories.py: corrige a regra de RAM (o 'MHz' colado ao número, ex. '2666MHz', não era reconhecido).
2. stores.py: acrescenta o carregamento do registo automático (data/stores_auto.json).
3. .gitignore: acrescenta os ficheiros gerados da pasta data/.

Pode correr-se várias vezes: o que já estiver feito não é repetido.
Uso (na raiz do projeto, com o venv ativo): python scripts\\aplicar_correcoes.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ROOT / "backend" / "agents" / "group3_logic" / "categories.py"
STORES = ROOT / "backend" / "agents" / "group2_search" / "stores.py"
GITIGNORE = ROOT / ".gitignore"

LOADER = '''

import json as _json
from backend.config import DATA_DIR as _DATA_DIR


def _load_auto_stores() -> None:
    path = _DATA_DIR / "stores_auto.json"
    if not path.exists():
        return
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for key, cfg in data.items():
        if key not in STORES and isinstance(cfg, dict) and not cfg.get("disabled"):
            STORES[key] = cfg


_load_auto_stores()
'''

IGNORE_LINES = [
    "data/store_health.json",
    "data/lojas_resultado*.csv",
    "data/generated_live.csv",
    "data/auto_selectors_report.csv",
    "data/stores_generated.py",
    "data/lojas_baixo_medio.csv",
]


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:   # newline="": mantém CRLF/LF como está
        return f.read()


def write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def fix_categories() -> str:
    if not CATEGORIES.exists():
        return "ERRO: categories.py não encontrado"
    text = read(CATEGORIES)
    bad, good = "(?:\\bmhz\\b|", "(?:mhz\\b|"
    if bad in text:
        write(CATEGORIES, text.replace(bad, good))
        return "categories.py: regra de RAM corrigida"
    if good in text:
        return "categories.py: já estava corrigido"
    return "AVISO: categories.py não tem a regra de RAM (a atualizacao_4 foi copiada?)"


def add_loader() -> str:
    if not STORES.exists():
        return "ERRO: stores.py não encontrado"
    text = read(STORES)
    if "_load_auto_stores" in text:
        return "stores.py: loader já existia"
    eol = "\r\n" if "\r\n" in text else "\n"
    block = LOADER.replace("\n", eol)
    write(STORES, text.rstrip("\r\n") + eol + block)
    return "stores.py: loader do registo automático acrescentado"


def fix_gitignore() -> str:
    text = read(GITIGNORE) if GITIGNORE.exists() else ""
    eol = "\r\n" if "\r\n" in text else "\n"
    present = {line.strip() for line in text.splitlines()}
    missing = [line for line in IGNORE_LINES if line not in present]
    if not missing:
        return ".gitignore: já tinha as linhas"
    base = text.rstrip("\r\n")
    write(GITIGNORE, (base + eol if base else "") + eol.join(missing) + eol)
    return f".gitignore: acrescentadas {len(missing)} linhas"


def main() -> None:
    for step in (fix_categories, add_loader, fix_gitignore):
        print(step())
    print("\nA seguir:")
    print('  python -c "from backend.agents.group2_search.stores import STORES; print(len(STORES))"   (esperado: 16)')
    print("  python -m pytest tests -q   (esperado: 220 passed)")


if __name__ == "__main__":
    main()
