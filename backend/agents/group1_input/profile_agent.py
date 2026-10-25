from backend.db.database import SessionLocal
from backend.db.models import UserProfile
from backend.schemas.search import UserContext


def load_user_context() -> UserContext:
    with SessionLocal() as db:
        profile = db.query(UserProfile).first()
        if profile is None:
            return UserContext(country="PT", currency="EUR")
        return UserContext(
            country=profile.country,
            currency=profile.currency,
            excluded_stores=list(profile.excluded_stores or []),
        )