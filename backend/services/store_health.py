"""Saúde das lojas do registo automático (data/stores_auto.json).

Cada pesquisa regista, por loja, se devolveu itens. Uma loja automática que falha
DISABLE_AFTER vezes seguidas (erro ou 0 itens) fica desativada e deixa de ser pesquisada
até alguém a reativar (python -m scripts.store_status --reativar chave).

Só se acompanham lojas que estão no registo automático: as escritas à mão em stores.py
nunca são desativadas. O estado fica em data/store_health.json.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.config import DATA_DIR

HEALTH_FILE = DATA_DIR / "store_health.json"
AUTO_FILE = DATA_DIR / "stores_auto.json"
DISABLE_AFTER = 5


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def auto_keys(auto_path: Path = AUTO_FILE) -> set[str]:
    return set(_load(auto_path))


def record(store: str, n_items: int, error: bool = False, detail: str = "", *,
           path: Path = HEALTH_FILE, auto_path: Path = AUTO_FILE,
           now: Optional[datetime] = None) -> bool:
    """Regista o resultado de uma pesquisa. Devolve True se a loja ficou desativada agora."""
    if store not in auto_keys(auto_path):
        return False
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    data = _load(path)
    s = data.setdefault(store, {"runs": 0, "ok_runs": 0, "streak": 0, "disabled": False,
                                "last_items": 0, "last_run": "", "last_ok": "", "last_detail": ""})
    s["runs"] += 1
    s["last_run"] = stamp
    s["last_items"] = n_items
    if error or n_items <= 0:
        s["streak"] += 1
        s["last_detail"] = detail[:120] if detail else ("0 itens" if not error else "erro")
    else:
        s["streak"] = 0
        s["ok_runs"] += 1
        s["last_ok"] = stamp
        s["last_detail"] = ""
    newly = False
    if s["streak"] >= DISABLE_AFTER and not s["disabled"]:
        s["disabled"] = True
        newly = True
    _save(path, data)
    return newly


def is_disabled(store: str, path: Path = HEALTH_FILE) -> bool:
    return bool(_load(path).get(store, {}).get("disabled", False))


def reenable(store: str, path: Path = HEALTH_FILE) -> bool:
    data = _load(path)
    if store not in data:
        return False
    data[store]["disabled"] = False
    data[store]["streak"] = 0
    _save(path, data)
    return True


def status(path: Path = HEALTH_FILE) -> dict:
    return _load(path)


def priority(store: str, path: Path = HEALTH_FILE, auto_path: Path = AUTO_FILE) -> float:
    """0 a 1: lojas à mão = 1.0; lojas automáticas = taxa de pesquisas com itens (0.5 sem histórico)."""
    if store not in auto_keys(auto_path):
        return 1.0
    s = _load(path).get(store)
    if not s or s.get("runs", 0) < 3:
        return 0.5
    return s["ok_runs"] / s["runs"]
