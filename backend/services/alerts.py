from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Favorite, PriceHistory

AlertKind = Literal["target_reached", "price_drop", "suspicious_promo"]


class Alert(BaseModel):
    favorite_id: int
    kind: AlertKind
    title: str
    store: str
    price: float
    message: str


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)   # SQLite devolve datas sem fuso


def _history(db: Session, product_id: int) -> list[tuple[datetime, float]]:
    rows = db.scalars(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at)
    )
    return [(_aware(r.recorded_at), r.price) for r in rows]


def _suspicious_peak(
    window: list[tuple[datetime, float]], rise_pct: float, tol_pct: float
) -> Optional[float]:
    """Procura 'valor X -> subida >= rise_pct -> de volta a X (+/- tol_pct)'.
    Devolve o preço do pico, ou None."""
    if len(window) < 3:
        return None
    last = window[-1][1]
    for j in range(1, len(window) - 1):
        peak = window[j][1]
        if peak < last * (1 + rise_pct / 100):
            continue
        for i in range(j):
            if abs(window[i][1] - last) / last <= tol_pct / 100:
                return peak
    return None


def check_alerts(
    db: Session,
    drop_pct: float = 5.0,
    rise_pct: float = 10.0,
    window_days: int = 30,
    tol_pct: float = 2.0,
    now: Optional[datetime] = None,
) -> list[Alert]:
    """Alertas sobre os favoritos, a partir do histórico de preços.

    O histórico só tem os preços vistos quando pesquisaste o produto, e é o preço do
    artigo, sem portes. Os resultados são indicativos, não prova de nada."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=window_days)
    alerts: list[Alert] = []

    for fav in db.scalars(select(Favorite)):
        prod = fav.product
        hist = _history(db, prod.id)
        if not hist:
            continue
        last = hist[-1][1]

        def make(kind: AlertKind, message: str) -> Alert:
            return Alert(favorite_id=fav.id, kind=kind, title=prod.title,
                         store=prod.store, price=last, message=message)

        if fav.target_price is not None and last <= fav.target_price:
            alerts.append(make(
                "target_reached",
                f"Atingiu o preço-alvo: {last:.2f} € (alvo {fav.target_price:.2f} €).",
            ))

        window = [(t, p) for t, p in hist if t >= since]
        peak = _suspicious_peak(window, rise_pct, tol_pct)
        if peak is not None:
            alerts.append(make(
                "suspicious_promo",
                f"Possível promoção falsa: o preço subiu para {peak:.2f} € e voltou a "
                f"{last:.2f} €, o valor de antes da subida.",
            ))
            continue    # a descida é um efeito da subida: não a anunciar como boa notícia

        prev = next((p for _, p in reversed(hist) if p != last), None)
        if prev is not None and (prev - last) / prev * 100 >= drop_pct:
            alerts.append(make(
                "price_drop",
                f"Desceu {(prev - last) / prev * 100:.0f}%: de {prev:.2f} € para {last:.2f} €.",
            ))

    return alerts