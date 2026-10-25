import os
import time
from typing import Literal, Optional, get_args

from loguru import logger
from pydantic import BaseModel, ValidationError, conlist, create_model

from backend.agents.llm import ask_structured
from backend.services.cache import get_cached, make_key, set_cached

Category = Literal[
    "laptop", "desktop_pc", "graphics_card", "cpu", "motherboard",
    "ram", "ssd", "psu", "monitor", "other",
]

CACHE_VERSION = "category-v5"          # mudar se o prompt/formato mudar (invalida a cache antiga)
CACHE_TTL_MINUTES = 60 * 24 * 30       # 30 dias
BATCH_SIZE = 10
SKIP_MARK = "_skipped"                 # título largado por falta de tempo (não é uma categoria)
SKIP_TTL_MINUTES = 5                   # durante estes minutos não se volta a tentar (evita repetir ao mexer nos filtros)
CALL_TIMEOUT_S = 120.0                 # limite de UM pedido ao Ollama (o 1.º pode incluir o carregamento do modelo)
TIME_BUDGET_S = 270.0                  # tempo máximo a classificar por LLM numa pesquisa (4,5 min; ver aggregator.SCRAPE_BUDGET_S)
# Resposta compacta, LIGADA por defeito (CATEGORY_COMPACT=0 desliga). Em CPU o tempo é quase todo a
# gerar texto, por isso o modelo devolve só "id:categoria" por título (ex.: "3:laptop"), em vez de
# um objeto JSON. Medido com scripts/bench_compact.py: 31,8 s contra 53,6 s (20 títulos), 1
# diferença em 20. A 1.ª versão (lista sem ids) errava 8 em 20 e foi abandonada. Se mudares o
# prompt ou o formato, sobe o CACHE_VERSION.
COMPACT_OUTPUT = os.environ.get("CATEGORY_COMPACT", "1") != "0"
LAST_RUN: dict[str, int] = {"failed_titles": 0, "skipped_titles": 0}

SYSTEM = """És o Agente de Categorias de uma aplicação de compras.
Recebes uma lista numerada de títulos de produtos (em português ou espanhol).
Para cada título, indica a categoria do produto que está MESMO a ser vendido.
Categorias: laptop, desktop_pc, graphics_card, cpu, motherboard, ram, ssd, psu, monitor, other.
Regras:
- Um portátil ou um PC completo é laptop ou desktop_pc, mesmo que o título mencione RTX, RAM ou SSD.
- desktop_pc: títulos com 'PC', 'PC Gaming', 'Pc Gamer', 'Torre', 'Desktop' ou 'Computador de secretária',
  quando NÃO dizem portátil, laptop ou notebook.
- laptop: só computadores portáteis (título com portátil, laptop ou notebook, ou claramente um portátil,
  por exemplo MacBook). A palavra 'portátil' sozinha não chega: 'celular portátil' é um telemóvel.
- Smartphones, telemóveis, celulares, tablets, relógios, leitores de música e MP3/MP4 são other,
  mesmo que o título mencione RAM, ROM ou polegadas.
- ram: memórias RAM e kits de memória vendidos como componente (por exemplo Kingston Fury Beast 16GB DDR4,
  Corsair Vengeance DDR5, SODIMM). Nunca é other.
- graphics_card só se o artigo vendido for a placa gráfica em si.
- ssd: 'SSD' ou 'Unidade de Estado Sólido' vendidos como componente de armazenamento.
- Acessórios (caixas, suportes, cabos, pasta térmica, ventoinhas, coolers) são other.
- Se não tiveres a certeza, usa other. Não inventes.
- Devolve exatamente um item por título, com o mesmo id."""


_LAST_RULE = "- Devolve exatamente um item por título, com o mesmo id."
SYSTEM_COMPACT = SYSTEM.replace(
    _LAST_RULE,
    "- Devolve em \"answers\" exatamente um texto por título, no formato id:categoria (por exemplo 3:laptop), com o id do título.",
)


class TitleCategory(BaseModel):
    id: int
    category: Category


class CategoryBatch(BaseModel):
    items: list[TitleCategory]


def _compact_schema(n: int):
    codes = tuple(f"{i}:{c}" for i in range(n) for c in get_args(Category))
    Code = Literal[codes]  # type: ignore[valid-type]
    return create_model("CompactBatch", answers=(conlist(Code, min_length=n, max_length=n), ...))


def _from_compact(answers: list[str], n: int) -> CategoryBatch:
    items: list[TitleCategory] = []
    seen: set[int] = set()
    for a in answers:
        i, _, cat = a.partition(":")
        if i.isdigit() and 0 <= int(i) < n and int(i) not in seen:
            seen.add(int(i))
            items.append(TitleCategory(id=int(i), category=cat))
    return CategoryBatch(items=items)


def _ask(chunk: list[str]) -> CategoryBatch:
    user = "\n".join(f"{i}: {t}" for i, t in enumerate(chunk))
    if not COMPACT_OUTPUT:
        return ask_structured(SYSTEM, user, CategoryBatch, timeout=CALL_TIMEOUT_S)
    r = ask_structured(SYSTEM_COMPACT, user, _compact_schema(len(chunk)), timeout=CALL_TIMEOUT_S)
    return _from_compact(r.answers, len(chunk))


def classify_titles(titles: list[str], time_budget: Optional[float] = TIME_BUDGET_S) -> dict[str, str]:
    """Devolve {título: categoria}. Títulos que falharem ou que ficarem por classificar quando o
    tempo acaba ficam de fora (usar fallback). A ordem de `titles` é a prioridade: passa os
    títulos mais importantes primeiro. time_budget=None = sem limite."""
    unique = list(dict.fromkeys(t for t in titles if t and t.strip()))
    out: dict[str, str] = {}
    LAST_RUN["failed_titles"] = 0
    LAST_RUN["skipped_titles"] = 0
    deadline = None if time_budget is None else time.monotonic() + time_budget
    pending: list[str] = []

    for t in unique:
        cached = get_cached(make_key(CACHE_VERSION, t))
        if cached and cached.get("category") == SKIP_MARK:
            LAST_RUN["skipped_titles"] += 1
        elif cached and cached.get("category"):
            out[t] = cached["category"]
        else:
            pending.append(t)

    batch_times: list[float] = []     # duração dos lotes já feitos: prevê se o próximo cabe no tempo
    for i in range(0, len(pending), BATCH_SIZE):
        now = time.monotonic()
        estimate = sum(batch_times) / len(batch_times) if batch_times else 0.0
        if deadline is not None and (now >= deadline or now + estimate > deadline):
            LAST_RUN["skipped_titles"] += len(pending) - i
            for t in pending[i:]:
                set_cached(make_key(CACHE_VERSION, t), "category", {"category": SKIP_MARK},
                           ttl_minutes=SKIP_TTL_MINUTES)
            break
        chunk = pending[i:i + BATCH_SIZE]
        started = time.monotonic()
        try:
            batch = _ask(chunk)
            batch_times.append(time.monotonic() - started)
        except Exception as e:  # Ollama em baixo, JSON inválido, etc.
            logger.warning(f"Classificação por LLM falhou: {type(e).__name__}: {e}")
            LAST_RUN["failed_titles"] += len(chunk)
            if not isinstance(e, ValidationError):
                # Ollama lento ou em baixo (timeout, ligação): não insistir nos lotes seguintes
                # (nem repetir este lote a cada mudança de filtro na interface)
                rest = pending[i:]
                LAST_RUN["skipped_titles"] += len(rest) - len(chunk)
                for t in rest:
                    set_cached(make_key(CACHE_VERSION, t), "category", {"category": SKIP_MARK},
                               ttl_minutes=SKIP_TTL_MINUTES)
                break
            continue
        for item in batch.items:
            if 0 <= item.id < len(chunk):
                title = chunk[item.id]
                out[title] = item.category
                set_cached(
                    make_key(CACHE_VERSION, title), "category",
                    {"category": item.category}, ttl_minutes=CACHE_TTL_MINUTES,
                )
    return out