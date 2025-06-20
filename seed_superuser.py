from core.utils.db_session import SessionLocal
from core.models.models import User, Site, SiteMembership
import subprocess


def upgrade_db() -> None:
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Warning: could not apply migrations: {exc}")
from core.utils.auth import get_password_hash, verify_password


def main():
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email="admin").first()
        if existing:
            if not verify_password("12345678", existing.hashed_password):
                existing.hashed_password = get_password_hash("12345678")
                db.commit()
                print("Superuser password updated.")
            else:
                print("Superuser already exists.")
            return

        hashed_pw = get_password_hash("12345678")
        user = User(
            email="admin",
            hashed_password=hashed_pw,
            role="superadmin",
            is_active=True,
            theme="dark_colourful",
            font="sans",
            menu_style="tabbed",
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
    upgrade_db()
    main()
