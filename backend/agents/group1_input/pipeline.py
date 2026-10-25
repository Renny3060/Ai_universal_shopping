import re

from loguru import logger

from backend.agents.group1_input.compatibility_agent import derive_constraints
from backend.agents.group1_input.parser_agent import parse_text
from backend.agents.group1_input.profile_agent import load_user_context
from backend.agents.group1_input.specs_agent import build_specs
from backend.schemas.search import EnrichedQuery, ProductSpecs, SearchQuery
from backend.utils.query_cleaning import clean_search_term, extract_budget

# Preenchido quando o LLM falha; a interface e os scripts mostram um aviso.
LAST_RUN: dict[str, bool] = {"llm_failed": False}


# Medidas que indicam requisitos técnicos (16GB, 1TB, 144Hz, 750W, 15.6", 6 cores...).
SPEC_UNITS = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:gb|tb|mb|hz|w|watts?|pol|polegadas?|mah|mp|cores?|nucleos?)\b|\"", re.I)


def needs_specs(text: str, query: SearchQuery) -> bool:
    """O Agente 2 (LLM) só corre se houver requisitos a interpretar. Poupa uma chamada ao LLM
    (muitos segundos) em pedidos simples como 'RTX 5060 até 650€'."""
    return bool(query.must_have or query.nice_to_have or SPEC_UNITS.search(text))


def run_group1(text: str) -> EnrichedQuery:
    user = load_user_context()            # Agente 4 (BD)
    derived = derive_constraints(text)    # Agente 3 (regras)
    LAST_RUN["llm_failed"] = False

    try:
        query = parse_text(text)          # Agente 1 (LLM)
        specs = (build_specs(text, query) if needs_specs(text, query)   # Agente 2 (LLM)
                 else ProductSpecs(category="", requirements=[]))
    except Exception as e:                # Ollama desligado, timeout, JSON inválido...
        logger.warning(f"Grupo 1 sem LLM: {type(e).__name__}: {e}")
        LAST_RUN["llm_failed"] = True
        term = clean_search_term(text)
        query = SearchQuery(product_type="", keywords=term.split(), max_budget=extract_budget(text))        
        specs = ProductSpecs(category="", requirements=[])

    return EnrichedQuery(
        raw_text=text,
        query=query,
        specs=specs,
        derived_constraints=derived,
        user=user,
    )