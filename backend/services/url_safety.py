import ipaddress
from typing import Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field


class UrlCheck(BaseModel):
    ok: bool
    problems: list[str] = Field(default_factory=list)


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def check_url(url: str, store_base_url: Optional[str] = None,
              extra_domains: Optional[list[str]] = None) -> UrlCheck:
    """Filtro básico por regras sobre o endereço. Não garante que a página é segura.

    store_base_url: endereço base da loja (de stores.py). Se faltar, o domínio não é verificado."""
    if not url or not url.strip():
        return UrlCheck(ok=False, problems=["URL vazio."])

    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return UrlCheck(ok=False, problems=["URL malformado."])

    problems: list[str] = []

    if parts.scheme != "https":
        problems.append("Não usa HTTPS.")
    if not host:
        problems.append("Sem domínio.")
    if "@" in parts.netloc:
        problems.append("Contém '@' no endereço.")
    if port not in (None, 443):
        problems.append(f"Porta invulgar ({port}).")

    if host:
        try:
            ipaddress.ip_address(host)
            problems.append("O endereço é um IP, não um domínio.")
        except ValueError:
            pass
        if any(label.startswith("xn--") for label in host.split(".")):
            problems.append("Domínio com caracteres internacionais (punycode).")

    if store_base_url and host:
        allowed = [_strip_www((urlsplit(store_base_url).hostname or "").lower())]
        allowed += [_strip_www(d.lower()) for d in (extra_domains or [])]
        allowed = [a for a in allowed if a]
        h = _strip_www(host)
        if allowed and not any(h == a or h.endswith("." + a) for a in allowed):
            problems.append(f"Domínio ({host}) não pertence à loja ({allowed[0]}).")

    return UrlCheck(ok=not problems, problems=problems)