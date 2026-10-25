import re
import time
import unicodedata
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Optional

from backend.agents.group2_search.configurable_scraper import ConfigurableScraper
from backend.agents.group2_search.stores import STORES
from backend.config import settings
from backend.schemas.product import ProductResult
from backend.services import store_health
from backend.services.price_tracker import save_results

# Sufixos que mudam o modelo (5060 Ti, 7600 XT, 4070 Super...)
_SUFFIX = r"(ti|super|xtx|xt)\b"

# Capacidades (16gb, 1tb): quem as valida é o validador (spec_check), não este filtro
_CAPACITY_TOKEN = re.compile(r"^\d+(gb|tb|go)$")

_STOPWORDS = {"de", "da", "do", "das", "dos", "para", "com", "the", "and", "por", "um", "uma"}


def _fold(text: str) -> str:
    """Minúsculas e sem acentos."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

# Loja que respondeu sem produtos (bloqueios levantam exceção e ficam como erro real).
NO_RESULTS = "Sem resultados nesta loja para este termo."

# Orçamento de tempo do scraping (segundos). As lojas que não terminarem a tempo são largadas e
# continuam a carregar em segundo plano, por isso ficam na cache para a pesquisa seguinte.
SCRAPE_BUDGET_S = 210.0   # 3,5 min; com os 270 s do LLM (category_llm) a pesquisa fica sempre abaixo dos 10 min
MAX_WORKERS = 5
TIMEOUT_MSG = "Tempo esgotado: a loja demorou demasiado (continua a carregar para a cache)."
NOT_REACHED_MSG = "Não chegou a ser pesquisada (tempo esgotado)."
EMPTY_SUSPECT = "Possível bloqueio: a loja não devolveu produtos (página vazia)."

def _words_ok(title: str, query: str) -> bool:
    """Termos sem números (ex.: 'golf gti', 'capacete'): cada palavra tem de estar no título.
    Ignora palavras curtas e stopwords; tolera plural simples ('capacetes' casa 'capacete')."""
    t = _fold(title)
    for w in re.findall(r"[a-z]+", _fold(query)):
        if len(w) < 3 or w in _STOPWORDS:
            continue
        stem = w[:-1] if len(w) > 4 and w.endswith("s") else w
        if stem not in t:
            return False
    return True

# Palavras de 2 letras que NÃO são modelos (unidades, siglas comuns, sufixos tratados à parte).
_SHORT_SKIP = {"ti", "xt", "pc", "tv", "hd", "gb", "tb", "go", "mb", "hz", "kg", "cm", "mm", "ml",
               "em", "ou", "no", "na", "os", "as", "ao", "se", "el", "la", "le", "un", "en", "et"}


def _short_ok(title: str, query: str) -> bool:
    """Siglas de modelo de 2 letras (ex.: 'tt' em 'audi tt', 'cx' em 'mazda cx') têm de aparecer
    no título como palavra inteira. Só conta quando o termo tem 2 ou mais palavras, para
    'audi tt' não devolver A3, A4 ou Q7."""
    words = [w for w in re.findall(r"[a-z]+", _fold(query)) if w not in _STOPWORDS]
    if len(words) < 2:
        return True
    t = _fold(title)
    for w in words:
        if len(w) == 2 and w not in _SHORT_SKIP:
            if not re.search(rf"(?<![a-z0-9]){w}(?![a-z0-9])", t):
                return False
    return True


def _any_word_ok(title: str, query: str) -> bool:
    """Pelo menos uma palavra significativa do termo no título (plural simples tolerado).
    Termos sem palavras significativas não filtram nada."""
    t = _fold(title)
    words = [w for w in re.findall(r"[a-z]+", _fold(query)) if len(w) >= 3 and w not in _STOPWORDS]
    if not words:
        return True
    return any((w[:-1] if len(w) > 4 and w.endswith("s") else w) in t for w in words)

def relevant(title: str, keywords: str, trust_words: bool = False) -> bool:
    """Os números de modelo da pesquisa (ex.: 5060, 4060) têm de aparecer no título.
    Capacidades como 16gb ou 1tb são ignoradas aqui (o validador trata delas).
    Se o termo tem sufixo (Ti, Super, XT), o título tem de ter o mesmo sufixo;
    se não tem, o título não pode ter nenhum (5060 não aceita 5060 Ti).
    trust_words=True (loja com trust_search): a pesquisa da própria loja já filtra por
    palavras, por isso não se exige cada palavra no título (só os números de modelo)."""
    q = keywords.lower()
    t = title.lower()
    tokens = re.findall(r"[a-z0-9]+", q)
    must = [
        m for m in tokens
        if any(c.isdigit() for c in m) and not _CAPACITY_TOKEN.match(m)
    ]

    for m in must:
        if m not in t:
            return False
        q_suffix = re.search(rf"{re.escape(m)}\s*{_SUFFIX}", q)
        t_suffix = re.search(rf"{re.escape(m)}\s*{_SUFFIX}", t)
        if q_suffix:
            if not t_suffix or t_suffix.group(1) != q_suffix.group(1):
                return False
        elif t_suffix:
            return False
    if not any(any(c.isdigit() for c in m) for m in tokens):
        if trust_words:
            return _any_word_ok(title, keywords)
        return _words_ok(title, keywords) and _short_ok(title, keywords)
    # Com um número de modelo a sério (5060, 16gb, x5) o título já é filtrado acima; com só
    # números soltos (ex.: 'audi tt 2.0') as siglas de 2 letras também contam.
    has_model = any(any(c.isdigit() for c in m) and len(m) >= 3 for m in tokens)
    return True if (has_model or trust_words) else _short_ok(title, keywords)


def search_all(
    keywords: str,
    stores: Optional[list[str]] = None,
    excluded: Optional[list[str]] = None,
    save: bool = True,
    use_cache: bool = True,
    hint: Optional[str] = None,
    max_pages: Optional[int] = None,
    vertical: Optional[str] = None,
    time_budget: Optional[float] = SCRAPE_BUDGET_S,
) -> tuple[list[ProductResult], dict[str, str]]:
    """Pesquisa em todas as lojas em paralelo. Devolve (resultados por preço, erros por loja).

    hint: palavra da categoria (ex.: 'placa grafica'), acrescentada ao termo só nas
    lojas com use_hint=True em stores.py.
    max_pages: páginas por loja (por defeito, MAX_PAGES do .env). Só conta nas lojas
    com page_url em stores.py.
    time_budget: segundos máximos de espera pelas lojas (None = sem limite). As lojas mais
    fiáveis arrancam primeiro; as que não terminarem a tempo aparecem como erro e ficam a
    carregar em segundo plano (os resultados entram na cache para a próxima pesquisa)."""
    names = [s for s in (stores or list(STORES)) if s not in (excluded or [])]
    if vertical:
        names = [s for s in names if vertical in STORES[s].get("verticals", [])]
    if not stores:  # com lojas pedidas explicitamente (diagnóstico) não se salta nenhuma
        names = [n for n in names if not store_health.is_disabled(n)]
    names.sort(key=lambda n: -store_health.priority(n))   # estável: empate mantém a ordem
    pages = max_pages or settings.max_pages
    results: list[ProductResult] = []
    errors: dict[str, str] = {}

    if not names:
        errors["_config"] = "Todas as lojas estão excluídas (ver 'Lojas a excluir' / perfil)."
        return results, errors

    def run(name: str) -> list[ProductResult]:
        cfg = STORES[name]
        term = f"{hint} {keywords}".strip() if hint and cfg.get("use_hint") else keywords
        return ConfigurableScraper(name, cfg).search(term, use_cache=use_cache, max_pages=pages)

    deadline = None if time_budget is None else time.monotonic() + time_budget

    def phase(batch: list[str], workers: int) -> bool:
        """Corre as lojas de `batch` com `workers` threads, até ao prazo comum.
        Devolve True se o prazo esgotou antes de todas terminarem."""
        pool = ThreadPoolExecutor(max_workers=max(1, min(workers, len(batch))))
        futures = {pool.submit(run, n): n for n in batch}
        pending = set(futures)
        try:
            while pending:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise FuturesTimeout()
                done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                if not done:
                    raise FuturesTimeout()
                for fut in done:
                    name = futures[fut]
                    try:
                        items = fut.result()
                    except Exception as e:  # uma loja a falhar não pode parar as outras
                        errors[name] = f"{type(e).__name__}: {e}"
                        store_health.record(name, 0, error=True, detail=errors[name])
                        continue
                    store_health.record(name, len(items))
                    if not items:
                        # Loja "solo" (sensível a pedidos simultâneos): vazio após as tentativas
                        # é suspeito, não é "sem resultados".
                        errors[name] = EMPTY_SUSPECT if STORES[name].get("solo") else NO_RESULTS
                    results.extend(items)
            return False
        except FuturesTimeout:
            for fut in pending:
                name = futures[fut]
                if fut.cancel():            # ainda nem tinha arrancado: não é culpa da loja
                    errors[name] = NOT_REACHED_MSG
                else:                       # estava a correr e foi demasiado lenta
                    errors[name] = TIMEOUT_MSG
                    store_health.record(name, 0, error=True, detail="tempo esgotado")
            return True
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    # Lojas "solo" (ex.: Amazon.es devolve páginas vazias quando corre ao mesmo tempo que as
    # outras) só arrancam depois das restantes terminarem, uma de cada vez.
    solo_names = [n for n in names if STORES[n].get("solo")]
    par_names = [n for n in names if n not in solo_names]
    timed_out = phase(par_names, MAX_WORKERS) if par_names else False
    if solo_names:
        if timed_out:
            for n in solo_names:
                errors[n] = NOT_REACHED_MSG
        else:
            phase(solo_names, 1)

    results = [
        r for r in results
        if relevant(r.title, keywords, STORES.get(r.store, {}).get("trust_search", False))
    ]
    results.sort(key=lambda r: r.price)

    if save and results:
        save_results(results)
    return results, errors
