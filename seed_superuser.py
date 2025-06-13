import bcrypt

from app.utils.db_session import SessionLocal
from app.models.models import User


def main():
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email="barny@ces.net").first()
        if existing:
            print("Superuser already exists.")
            return

        hashed_pw = bcrypt.hashpw("C0pperpa!r".encode(), bcrypt.gensalt()).decode()
        user = User(
            email="barny@ces.net",
            hashed_password=hashed_pw,
            role="superadmin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print("Superuser created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

