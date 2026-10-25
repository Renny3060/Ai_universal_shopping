from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # necessário para FastAPI + SQLite
    echo=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fks(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependência FastAPI: abre e fecha a sessão por pedido."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()