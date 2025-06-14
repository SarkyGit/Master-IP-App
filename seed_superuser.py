from app.utils.db_session import SessionLocal
from app.models.models import User, Site, SiteMembership
from app.utils.auth import get_password_hash


def main():
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email="Barny@CESTechnologies.com").first()
        if existing:
            if existing.hashed_password != get_password_hash("C0pperpa!r"):
                existing.hashed_password = get_password_hash("C0pperpa!r")
                db.commit()
                print("Superuser password updated.")
            else:
                print("Superuser already exists.")
            return

        hashed_pw = get_password_hash("C0pperpa!r")
        user = User(
            email="Barny@CESTechnologies.com",
            hashed_password=hashed_pw,
            role="superadmin",
            is_active=True,
            theme="dark",
            font="sans",
        )
        db.add(user)
        db.commit()
        site = db.query(Site).first()
        if site:
            db.add(SiteMembership(user_id=user.id, site_id=site.id))
            db.commit()
        print("Superuser created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
