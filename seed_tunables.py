from app.utils.db_session import SessionLocal
from app.models.models import SystemTunable


def main():
    db = SessionLocal()
    try:
        if db.query(SystemTunable).first():
            print("Tunables already seeded")
            return
        samples = [
            SystemTunable(
                name="Enable SSH",
                value="true",
                function="SSH",
                file_type="sshd_config",
                data_type="bool",
            ),
            SystemTunable(
                name="Config Backup Count",
                value="10",
                function="Backup",
                file_type="application",
                data_type="text",
            ),
            SystemTunable(
                name="SNMP Version",
                value="v2c",
                function="SNMP",
                file_type="snmpd.conf",
                data_type="choice",
                options="v1,v2c,v3",
            ),
        ]
        db.add_all(samples)
        db.commit()
        print("Tunables seeded")
    finally:
        db.close()


if __name__ == "__main__":
    main()
