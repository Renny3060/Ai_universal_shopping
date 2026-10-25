import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.config import settings
from backend.db.database import SessionLocal
from backend.db.models import SearchCache


def make_key(store: str, query: str) -> str:
    return hashlib.sha256(f"{store}|{query.strip().lower()}".encode()).hexdigest()


def get_cached(key: str) -> Optional[dict]:
    with SessionLocal() as db:
        row = db.query(SearchCache).filter_by(cache_key=key).first()
        if row is None:
            return None
        exp = row.expires_at
        if exp.tzinfo is None:                      # SQLite devolve datas sem fuso
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return None
        return row.payload


def set_cached(key: str, store: str, payload: dict, ttl_minutes: Optional[int] = None) -> None:
    ttl = ttl_minutes or settings.cache_ttl_minutes
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        row = db.query(SearchCache).filter_by(cache_key=key).first()
        if row is None:
            row = SearchCache(cache_key=key, store=store, payload=payload,
                              created_at=now, expires_at=now + timedelta(minutes=ttl))
            db.add(row)
        else:
            row.payload = payload
            row.created_at = now
            row.expires_at = now + timedelta(minutes=ttl)
        db.commit()