import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
from core.utils.db_session import SessionLocal, reset_pk_sequence
from core.models.models import User, Site, SiteMembership, SchemaValidationIssue
import subprocess


def upgrade_db() -> None:
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Warning: could not apply migrations: {exc}")
from core.utils.auth import get_password_hash, verify_password
from core.utils.schema import validate_schema_integrity


def main():
    check = validate_schema_integrity()
    if not check["valid"]:
        db = SessionLocal()
        try:
            for t in check["missing_tables"]:
                db.add(SchemaValidationIssue(table_name=t, issue_type="missing_table"))
            for t, cols in check["missing_columns"].items():
                for c in cols:
                    db.add(SchemaValidationIssue(table_name=t, column_name=c, issue_type="missing_column"))
            for t, cols in check["mismatched_columns"].items():
                for c, types in cols.items():
                    db.add(
                        SchemaValidationIssue(
                            table_name=t,
                            column_name=c,
                            expected_type=types[0],
                            actual_type=types[1],
                            issue_type="mismatched_column",
                        )
                    )
            db.commit()
        finally:
            db.close()
        print("Schema validation failed. Aborting seeding.")
        return

    db = SessionLocal()
    reset_pk_sequence(db, User)
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
        try:
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()
        site = db.query(Site).first()
        if site:
            try:
                db.add(SiteMembership(user_id=user.id, site_id=site.id))
                db.commit()
            except Exception:
                db.rollback()
        print("Superuser created.")
    finally:
        db.close()


if __name__ == "__main__":
    upgrade_db()
    main()
