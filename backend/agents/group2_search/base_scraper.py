import time
from urllib.parse import quote_plus

from loguru import logger

from backend.agents.group2_search.block_detector import detect_block
from backend.agents.group2_search.browser import fetch_html
from backend.schemas.product import ProductResult
from backend.services.cache import get_cached, make_key, set_cached

# Pausas (segundos) entre tentativas na página 1. Tentativas = 1 + len(RETRY_PAUSES).
RETRY_PAUSES = (4.0, 10.0)
_sleep = time.sleep   # substituível nos testes


class ScrapeBlocked(Exception):
    """A loja devolveu uma página de bloqueio ou captcha em vez de resultados."""


class BaseScraper:
    store: str = ""
    wait_selector: str | None = None

    def build_url(self, keywords: str) -> str:
        raise NotImplementedError

    def build_page_url(self, keywords: str, page: int) -> str | None:
        """URL da página N (N >= 2). None = a loja não tem paginação configurada."""
        return None

    def parse(self, html: str) -> list[ProductResult]:
        raise NotImplementedError

    def _fetch_page(self, keywords: str, page: int, use_cache: bool, debug: bool) -> list[ProductResult]:
        suffix = "" if page == 1 else f"|p{page}"          # a página 1 mantém a chave antiga
        key = make_key(self.store, keywords + suffix)
        if use_cache:
            cached = get_cached(key)
            if cached is not None:
                return [ProductResult(**i) for i in cached["items"]]

        url = self.build_url(keywords) if page == 1 else self.build_page_url(keywords, page)

        # Só a página 1 tem tentativas extra: uma página 2 vazia é o fim normal dos resultados.
        max_retries = len(RETRY_PAUSES) if page == 1 else 0
        retries = 0
        clean_empty_retried = False
        items: list[ProductResult] = []

        while True:
            problem: Exception | None = None
            try:
                html = fetch_html(
                    url,
                    wait_selector=self.wait_selector,
                    save_as=f"{self.store}.html" if debug else None,
                )
                items = self.parse(html)
                if items:
                    break
                reason = detect_block(html)
                if reason:
                    problem = ScrapeBlocked(f"bloqueado: {reason}")
            except Exception as e:                      # erro do browser, timeout, etc.
                problem = e

            if retries >= max_retries:
                if problem is not None and page == 1:
                    raise problem
                break
            if problem is None:                          # página limpa mas sem produtos
                if clean_empty_retried:
                    break
                clean_empty_retried = True               # só uma repetição neste caso

            pause = RETRY_PAUSES[retries]
            retries += 1
            logger.warning(
                f"{self.store} página {page}: "
                f"{'sem produtos' if problem is None else type(problem).__name__ + ': ' + str(problem)}"
                f"; nova tentativa {retries}/{max_retries} daqui a {pause:.0f}s"
            )
            _sleep(pause)

        if items:                                    # nunca guardar resultados vazios
            set_cached(key, self.store, {"items": [i.model_dump() for i in items]})
        return items

    def search(self, keywords: str, use_cache: bool = True, debug: bool = False,
               max_pages: int = 1) -> list[ProductResult]:
        results: list[ProductResult] = []
        seen: set[str] = set()
        for page in range(1, max(1, max_pages) + 1):
            if page > 1 and self.build_page_url(keywords, page) is None:
                break                                # loja sem paginação configurada
            try:
                items = self._fetch_page(keywords, page, use_cache, debug)
            except Exception as e:
                if page == 1:
                    raise                            # sem página 1 não há nada a mostrar
                logger.warning(f"{self.store} página {page} falhou, mantidos {len(results)} "
                               f"resultados: {type(e).__name__}: {e}")
                break
            new = [i for i in items if i.external_id not in seen]
            if not new:
                break                                # página vazia ou só repetidos
            seen.update(i.external_id for i in new)
            results.extend(new)
        return results

    @staticmethod
    def encode(keywords: str) -> str:
        return quote_plus(keywords)