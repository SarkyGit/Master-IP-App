# User Manual

This guide explains how to navigate the Master IP application, manage settings and resolve common issues.

## Navigation Overview

The main menu exposes **Inventory**, **Network** and **Admin** sections. Inventory pages manage devices, reports and related settings. The Network menu covers dashboards, configuration tasks and status utilities. Administrators see additional pages for system settings and cloud synchronisation.

## Core Data Fields

Devices and other records rely on a set of common variables:

- **Location** – physical location of the device. Locations are created under *Admin → Locations* and assigned when editing a device.
- **Site** – logical site used for cloud replication. Sites are managed from *Admin → Sites*.
- **Device Type** – model category for hardware. Defined under *Admin → Inventory Settings*.
- **VLAN** – network VLAN number. Added from *Network → Network Settings → VLANs*.
- **SSH Profile** – credentials for SSH actions. Managed from *Network → Network Settings → SSH Credentials*.
- **SNMP Profile** – community or v3 profile for SNMP polling. Configured under *Network → Network Settings → SNMP Profiles*.
- **Tags** – free‑form labels applied to devices for filtering.
- **System Tunables** – application options stored in the database. Accessible at *Admin → System Tunables*.

### System Tunables

Each tunable has a **name**, **value**, **function** group and optional choices. Key options include:

- **Enable SSH** – turn the built‑in SSH service on or off.
- **Config Backup Count** – number of configuration backups to keep.
- **SNMP Version** – protocol version used when querying devices.
- **Google Service Account JSON** – path to Google Sheets credentials.
- **Google Spreadsheet ID** – target spreadsheet identifier.
- **GOOGLE_MAPS_API_KEY** – API key for the Maps JavaScript library.
- **Netbird API URL / Token** – connection info for Netbird integration.
- **Cloud Base URL / API Key / Site ID** – parameters for cloud synchronisation.
- **Enable Cloud Sync** – toggles the periodic heartbeat and sync workers.
- **Queue Interval** – seconds between processing queued config pushes.
- **Port History Retention Days** – days to keep historical port data.
- **SSH Timeout Seconds** – inactivity timeout for the web terminal.
- **Default SNMP Version** – preselected version when creating profiles.
- **Enable SNMP Trap Listener** and **SNMP Trap Port** – control the trap listener.
- **Enable Syslog Listener** and **Syslog Port** – control the syslog listener.
- **SMTP Server / Port / Username / Password** – outgoing mail settings.
- **Email From** – default sender address.
- **App Version** – informational string shown on the settings page.
- **ALLOW_SELF_UPDATE** and **FORCE_REBOOT_ON_UPDATE** – update behaviour.

## Environment Variables

The server also reads configuration from the environment:

- `DATABASE_URL` – PostgreSQL connection string.
- `SECRET_KEY` – signing key for sessions and tokens (change before deploying).
- `TOKEN_TTL` – token lifetime in seconds (default 3600).
- `SESSION_TTL` – session cookie lifetime (default 43200).
- `ROOT_PATH` – optional URL prefix when behind a proxy.
- `ENABLE_TRAP_LISTENER` and `SNMP_TRAP_PORT` – enable and configure the trap listener.
- `ENABLE_SYSLOG_LISTENER` and `SYSLOG_PORT` – enable and configure the syslog listener.
- `QUEUE_INTERVAL` and `PORT_HISTORY_RETENTION_DAYS` – worker scheduling values.
- `WORKERS`, `TIMEOUT`, `PORT` and `AUTO_SEED` – options used by `start.sh`.
- `ROLE` – set to `local` or `cloud` to control sync behaviour.
- `ENABLE_CLOUD_SYNC` – disable cloud sync when set to `0`.
- `ENABLE_SYNC_PUSH_WORKER` – disable pushing local changes.
- `ENABLE_SYNC_PULL_WORKER` – disable pulling updates from the cloud.
- `ENABLE_BACKGROUND_WORKERS` – disable to skip queue and scheduler startup.
- `STATIC_DIR` – directory for uploaded images and other static assets.
- `CLOUD_BASE_URL` – base URL of the cloud server (overrides tunable).
- `SYNC_PUSH_URL` and `SYNC_PULL_URL` – custom sync endpoints.
- `SYNC_API_KEY` – bearer token sent with sync requests.

## Error States and Resolutions

- **Red Table Row** – a device or VLAN row highlighted in dark red indicates a conflict between the local record and the cloud. Open the alert icon in the Actions column or visit *Reports → Conflicts* to merge the data. Once resolved the row colour returns to normal.
- **Duplicate Highlighting** – cells with duplicate IP, MAC or asset tags appear with a red dot and tooltip. Review the duplicates report under *Inventory → Reports → Duplicates* and edit or remove the extra entries.
- **Unsynced Data Warning** – the update page shows "Unsynced Data" when local changes have not been pushed to the cloud. Use *Admin → Cloud Sync / API's* to run a manual sync before updating.
- **Terminal Disconnected** – if the web terminal only shows "*** Disconnected ***" ensure the `websockets` Python package is installed on the server.

## Further Help

See the README for installation instructions. Administrators can consult this manual at `/help/manual` within the application.
