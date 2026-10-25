from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(DATA_DIR / 'shopping.db').as_posix()}"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    default_country: str = "PT"
    default_currency: str = "EUR"
    cache_ttl_minutes: int = 60
    max_pages: int = 1   # páginas lidas por loja (só se a loja tiver page_url em stores.py)


settings = Settings()