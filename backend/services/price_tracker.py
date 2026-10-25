from datetime import datetime, timedelta, timezone

from backend.db.database import SessionLocal
from backend.db.models import PriceHistory, Product
from backend.schemas.product import ProductResult

MIN_REPEAT_HOURS = 6   # não regista o mesmo preço mais do que uma vez de 6 em 6 horas


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def save_results(results: list[ProductResult], store_cfgs: dict | None = None) -> int:
    """Grava produtos e regista o preço no histórico. Devolve nº de preços registados."""
    from backend.agents.group2_search.stores import STORES
    from backend.services.tax_calculator import calc_taxes

    cfgs = STORES if store_cfgs is None else store_cfgs
    now = datetime.now(timezone.utc)
    recorded = 0

    with SessionLocal() as db:
        for r in results:
            prod = db.query(Product).filter_by(store=r.store, external_id=r.external_id).first()
            if prod is None:
                prod = Product(
                    store=r.store, external_id=r.external_id, title=r.title, url=r.url,
                    image_url=r.image_url, seller_name=r.seller_name,
                    seller_rating=r.seller_rating, origin_country=r.origin_country,
                    condition=r.condition,
                )
                db.add(prod)
                db.flush()
            else:
                prod.title, prod.url, prod.image_url = r.title, r.url, r.image_url
                if r.seller_name:
                    prod.seller_name = r.seller_name
                prod.last_seen = now

            last = (
                db.query(PriceHistory)
                .filter_by(product_id=prod.id)
                .order_by(PriceHistory.recorded_at.desc())
                .first()
            )
            changed = last is None or last.price != r.price
            old = last is not None and now - _aware(last.recorded_at) > timedelta(hours=MIN_REPEAT_HOURS)

            if changed or old:
                cfg = cfgs.get(r.store) or {}
                shipping_known = r.shipping is not None
                shipping = r.shipping if shipping_known else 0.0
                taxes, _ = calc_taxes(
                    r.price, shipping,
                    cfg.get("region", "EU"),
                    cfg.get("duty_rate", 0.0),
                    cfg.get("low_value_flat_duty", 0.0),
                )
                db.add(PriceHistory(
                    product_id=prod.id, price=r.price, shipping=shipping,
                    shipping_known=shipping_known, taxes=taxes,
                    total_cost=r.price + shipping + taxes, currency=r.currency,
                    in_stock=r.in_stock, recorded_at=now,
                ))
                recorded += 1
        db.commit()
    return recorded