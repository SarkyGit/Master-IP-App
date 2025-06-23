import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.utils.db_session import SessionLocal
from core.models.models import SystemTunable
from core.utils.schema import safe_alembic_upgrade
import subprocess


def upgrade_db() -> None:
    try:
        safe_alembic_upgrade()
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Warning: could not apply migrations: {exc}")


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
            SystemTunable(
                name="GOOGLE_MAPS_API_KEY",
                value="",
                function="Google Maps",
                file_type="application",
                data_type="text",
                description="API key for Google Maps JavaScript",
            ),
            SystemTunable(
                name="Netbird API URL",
                value="https://api.netbird.io/api",
                function="Netbird",
                file_type="application",
                data_type="text",
                description="Base URL of the Netbird API",
            ),
            SystemTunable(
                name="Netbird API Token",
                value="",
                function="Netbird",
                file_type="application",
                data_type="text",
                description="Bearer token for Netbird API access",
            ),
            SystemTunable(
                name="Cloud Base URL",
                value="http://cloud",
                function="Sync",
                file_type="application",
                data_type="text",
                description="Base URL of the cloud server",
            ),
            SystemTunable(
                name="Cloud API Key",
                value="",
                function="Sync",
                file_type="application",
                data_type="text",
                description="API key used for cloud synchronization",
            ),
            SystemTunable(
                name="Cloud Site ID",
                value="1",
                function="Sync",
                file_type="application",
                data_type="text",
                description="Unique identifier for this local site",
            ),
            SystemTunable(
                name="Enable Cloud Sync",
                value="false",
                function="Sync",
                file_type="application",
                data_type="bool",
                description="Toggle periodic cloud heartbeat and sync",
            ),
            # ----- Newly added tunables -----
            SystemTunable(
                name="Queue Interval",
                value="60",
                function="Scheduler",
                file_type="application",
                data_type="text",
                description="Seconds between processing queued config pushes",
            ),
            SystemTunable(
                name="Port History Retention Days",
                value="60",
                function="Scheduler",
                file_type="application",
                data_type="text",
                description="Days to keep historical port status records",
            ),
            SystemTunable(
                name="SSH Timeout Seconds",
                value="900",
                function="SSH",
                file_type="application",
                data_type="text",
                description="Inactivity timeout for the web terminal",
            ),
            SystemTunable(
                name="Default SNMP Version",
                value="2c",
                function="SNMP",
                file_type="snmpd.conf",
                data_type="choice",
                options="v1,v2c,v3",
                description="Default SNMP version when creating profiles",
            ),
            SystemTunable(
                name="Enable SNMP Trap Listener",
                value="false",
                function="SNMP",
                file_type="application",
                data_type="bool",
                description="Start trap listener on startup",
            ),
            SystemTunable(
                name="SNMP Trap Port",
                value="162",
                function="SNMP",
                file_type="application",
                data_type="text",
                description="Port for incoming SNMP traps",
            ),
            SystemTunable(
                name="Enable Syslog Listener",
                value="false",
                function="Logging",
                file_type="application",
                data_type="bool",
                description="Start syslog listener on startup",
            ),
            SystemTunable(
                name="Syslog Port",
                value="514",
                function="Logging",
                file_type="application",
                data_type="text",
                description="Port for incoming syslog messages",
            ),
            SystemTunable(
                name="SMTP Server",
                value="",
                function="Email",
                file_type="application",
                data_type="text",
                description="Hostname of the SMTP server",
            ),
            SystemTunable(
                name="SMTP Port",
                value="25",
                function="Email",
                file_type="application",
                data_type="text",
                description="TCP port for the SMTP server",
            ),
            SystemTunable(
                name="SMTP Username",
                value="",
                function="Email",
                file_type="application",
                data_type="text",
                description="Username for SMTP authentication",
            ),
            SystemTunable(
                name="SMTP Password",
                value="",
                function="Email",
                file_type="application",
                data_type="text",
                description="Password for SMTP authentication",
            ),
            SystemTunable(
                name="Email From",
                value="noreply@example.com",
                function="Email",
                file_type="application",
                data_type="text",
                description="Default sender address for outgoing mail",
            ),
            SystemTunable(
                name="App Version",
                value="1.0.0",
                function="General",
                file_type="application",
                data_type="text",
                description="Deployed application version",
            ),
            SystemTunable(
                name="ALLOW_SELF_UPDATE",
                value="true",
                function="General",
                file_type="application",
                data_type="bool",
                description="Allow updating the app from the UI",
            ),
            SystemTunable(
                name="FORCE_REBOOT_ON_UPDATE",
                value="false",
                function="General",
                file_type="application",
                data_type="bool",
                description="Reboot after update when system files change",
            ),
        ]
        try:
            db.add_all(samples)
            db.commit()
        except Exception:
            db.rollback()
        print("Tunables seeded")
    finally:
        db.close()


if __name__ == "__main__":
    upgrade_db()
    main()
