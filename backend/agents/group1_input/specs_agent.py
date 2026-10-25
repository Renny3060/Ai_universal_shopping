from backend.agents.llm import ask_structured
from backend.schemas.search import ProductSpecs, SearchQuery

SYSTEM = """És o Agente de Especificações. Transformas requisitos em linguagem natural
numa lista rigorosa de requisitos técnicos.
Regras:
- Só incluis requisitos que o utilizador pediu. NUNCA acrescentes requisitos teus.
- attribute em snake_case (ex.: gpu, ram_gb, storage_gb, cpu_brand, screen_inches).
- operator: '>=' para mínimos, '<=' para máximos, '==' para valores exatos,
  'contains' para marcas ou modelos (ex.: gpu contains RTX).
- mandatory = true para requisitos obrigatórios, false para preferências.
- value é sempre texto; os números vão sem unidade, e a unidade vai em 'unit'."""


def build_specs(raw_text: str, query: SearchQuery) -> ProductSpecs:
    user = (
        f"Pedido original: {raw_text}\n\n"
        f"Parâmetros já extraídos: {query.model_dump_json()}"
    )
    return ask_structured(SYSTEM, user, ProductSpecs)