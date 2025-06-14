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
        ]
        db.add_all(samples)
        db.commit()
        print("Tunables seeded")
    finally:
        db.close()


if __name__ == "__main__":
    main()
