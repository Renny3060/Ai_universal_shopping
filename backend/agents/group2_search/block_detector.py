import re

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

_TITLE_WORDS = (
    "just a moment", "attention required", "access denied", "are you a robot",
    "verify you are human", "captcha", "acesso negado", "pardon our interruption",
    "robot check", "verifica que", "não és um robô", "unusual traffic",
)

_MARKERS = (
    "cf-challenge", "challenge-platform", "g-recaptcha", "h-captcha",
    "hcaptcha.com/1/api", "px-captcha", "captcha-delivery.com", "geo.captcha-delivery",
)

SMALL_PAGE_CHARS = 150_000


def detect_block(html: str) -> str | None:
    """Devolve o motivo do bloqueio ou None. Conservador: páginas grandes só são
    consideradas bloqueadas pelo título; marcadores só contam em páginas pequenas."""
    if not html or len(html.strip()) < 500:
        return "página vazia ou quase vazia"

    m = _TITLE_RE.search(html)
    title = re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else ""
    for w in _TITLE_WORDS:
        if w in title:
            return f"título suspeito: '{title[:80]}'"

    if len(html) < SMALL_PAGE_CHARS:
        low = html.lower()
        for mk in _MARKERS:
            if mk in low:
                return f"marcador anti-bot: {mk}"
    return None