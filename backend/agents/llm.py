from typing import Optional, Type, TypeVar

import ollama
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from backend.config import settings

T = TypeVar("T", bound=BaseModel)

KEEP_ALIVE = "30m"   # mantém o modelo carregado entre pedidos (evita recarregar em cada lote)

_client = ollama.Client(host=settings.ollama_base_url, timeout=120)

def ping() -> str:
    """Teste rápido: confirma que o Ollama responde."""
    r = _client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": "Responde apenas com: OK"}],
        options={"temperature": 0},
    )
    return r["message"]["content"].strip()


@retry(retry=retry_if_exception_type(ValidationError), stop=stop_after_attempt(3))
def ask_structured(system: str, user: str, schema: Type[T], temperature: float = 0.0,
                   timeout: Optional[float] = None) -> T:
    """Pede ao modelo uma resposta que cumpra EXATAMENTE o schema Pydantic.
    timeout (s) = limite só para este pedido; sem valor usa o do cliente (120 s)."""
    client = _client if timeout is None else ollama.Client(host=settings.ollama_base_url, timeout=timeout)
    r = client.chat(
        model=settings.ollama_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format=schema.model_json_schema(),
        options={"temperature": temperature},
        keep_alive=KEEP_ALIVE,
    )
    return schema.model_validate_json(r["message"]["content"])