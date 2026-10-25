from sqlalchemy import text

from backend.db.database import engine


def main() -> None:
    with engine.begin() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(price_history)"))]
        if "shipping_known" in cols:
            print("shipping_known já existe")
            return
        conn.execute(text("ALTER TABLE price_history ADD COLUMN shipping_known BOOLEAN"))
        print("Coluna shipping_known adicionada (NULL = histórico antigo)")


if __name__ == "__main__":
    main()