from backend.config import settings
from backend.db.database import Base, SessionLocal, engine
from backend.db import models  # noqa: F401  (regista as tabelas)
from backend.db.models import FavoriteFolder, UserProfile


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.query(UserProfile).count() == 0:
            db.add(UserProfile(
                country=settings.default_country,
                currency=settings.default_currency,
                excluded_stores=[],
                notification_prefs={"price_drop": True},
            ))
        if db.query(FavoriteFolder).count() == 0:
            db.add_all([FavoriteFolder(name="Geral"), FavoriteFolder(name="Build PC")])
        db.commit()

        print("Base de dados criada em:", settings.database_url)


if __name__ == "__main__":
    init_db()