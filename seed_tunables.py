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
                description="Toggle the SSH service on or off",
            ),
            SystemTunable(
                name="Config Backup Count",
                value="10",
                function="Backup",
                file_type="application",
                data_type="text",
                description="Number of configuration backups to keep",
            ),
            SystemTunable(
                name="SNMP Version",
                value="v2c",
                function="SNMP",
                file_type="snmpd.conf",
                data_type="choice",
                options="v1,v2c,v3",
                description="SNMP protocol version used for device queries",
            ),
            SystemTunable(
                name="Google Service Account JSON",
                value="service_account.json",
                function="Google Sheets",
                file_type="application",
                data_type="text",
                description="Path to service account credentials",
            ),
            SystemTunable(
                name="Google Spreadsheet ID",
                value="",
                function="Google Sheets",
                file_type="application",
                data_type="text",
                description="Target spreadsheet ID",
            ),
        ]
        db.add_all(samples)
        db.commit()
        print("Tunables seeded")
    finally:
        db.close()


if __name__ == "__main__":
    main()
