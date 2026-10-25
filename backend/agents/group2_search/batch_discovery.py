import csv
import re
from pathlib import Path
from urllib.parse import urlsplit

# Termo de teste por categoria e língua do país da loja. Só palavras comuns e genéricas:
# o objetivo é a loja devolver muitos produtos, para testar JSON-LD e pistas de CSS.
TERMS: dict[str, dict[str, str]] = {
    "hardware": {"pt": "ssd 1tb", "es": "ssd 1tb", "fr": "ssd 1to", "de": "ssd 1tb"},
    "eletronica": {"pt": "televisão", "es": "televisor", "fr": "télévision", "de": "fernseher"},
    "moto": {"pt": "capacete moto", "es": "casco moto", "fr": "casque moto", "de": "motorradhelm"},
    "auto": {"pt": "pneus", "es": "neumáticos", "fr": "pneus", "de": "reifen"},
    "casa": {"pt": "aspirador", "es": "aspirador", "fr": "aspirateur", "de": "staubsauger"},
    "desporto": {"pt": "sapatilhas", "es": "zapatillas", "fr": "baskets", "de": "sneaker"},
    "moda": {"pt": "sapatilhas", "es": "zapatillas", "fr": "baskets", "de": "sneaker"},
    "saude": {"pt": "champô", "es": "champú", "fr": "shampoing", "de": "shampoo"},
    "livros": {"pt": "lego", "es": "lego", "fr": "lego", "de": "lego"},
}
COUNTRY_LANG = {"PT": "pt", "ES": "es", "FR": "fr", "DE": "de"}

# Estados possíveis de uma loja depois de testada
OK_JSONLD = "ok_jsonld"            # pronta: só search_url e base_url
NEEDS_CSS = "precisa_css"          # pesquisa funciona, mas sem JSON-LD: seletores a partir do HTML
BLOCKED = "bloqueada"              # desafio anti-bot
NO_BOX = "sem_caixa"               # não encontrei a caixa de pesquisa
NO_TERM_IN_URL = "sem_termo_no_url"  # pesquisa por POST/JavaScript
OPEN_ERROR = "erro_abertura"       # domínio não abre (pode estar inventado ou em baixo)


def category_key(categoria: str) -> str:
    c = categoria.lower()
    if "hardware" in c or "inform" in c:
        return "hardware"
    if "eletr" in c:
        return "eletronica"
    if "moto" in c:
        return "moto"
    if "carro" in c or "auto" in c or "peças" in c or "pecas" in c:
        return "auto"
    if "casa" in c or "jardim" in c:
        return "casa"
    if "desporto" in c or "outdoor" in c:
        return "desporto"
    if "moda" in c or "calçado" in c or "calcado" in c:
        return "moda"
    if "super" in c or "saúde" in c or "saude" in c or "beleza" in c:
        return "saude"
    return "livros"


def term_for(categoria: str, pais: str) -> str:
    lang = COUNTRY_LANG.get(pais.strip().upper(), "pt")
    return TERMS[category_key(categoria)][lang]


def host_of(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def read_candidates(path: Path) -> list[dict]:
    """Lê o CSV do Gemini (UTF-8, com ou sem BOM). Ignora linhas sem URL http(s)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        if re.match(r"^https?://", r.get("url_inicial", "")):
            out.append(r)
    return out


def drop_known(rows: list[dict], known_hosts: set[str]) -> list[dict]:
    """Tira lojas repetidas (mesmo domínio) e as que já estão em STORES."""
    seen = set(known_hosts)
    out = []
    for r in rows:
        h = host_of(r["url_inicial"])
        if h in seen:
            continue
        seen.add(h)
        out.append(r)
    return out


def known_hosts_from_stores(stores: dict) -> set[str]:
    return {host_of(cfg["base_url"]) for cfg in stores.values() if cfg.get("base_url")}


def classify(*, opened: bool, blocked: bool, found_box: bool, has_template: bool, n_products: int) -> str:
    if not opened:
        return OPEN_ERROR
    if blocked:
        return BLOCKED
    if not found_box:
        return NO_BOX
    if not has_template:
        return NO_TERM_IN_URL
    return OK_JSONLD if n_products > 0 else NEEDS_CSS