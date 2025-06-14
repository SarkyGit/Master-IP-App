from sqlalchemy.orm import Session
from puresnmp import PyWrapper
from app.models.models import Device, SSHCredential
from app.utils.audit import log_audit

PLATFORM_MAP = {
    "cisco ios": "Cisco IOS",
    "edgeswitch": "Ubiquiti EdgeSwitch",
    "edgeos": "Ubiquiti EdgeSwitch",
    "ruckus": "Ruckus",
    "fastiron": "Ruckus",
}

DEFAULT_SSH_PROFILES = {
    "Cisco IOS": "Cisco Default",
    "Ubiquiti EdgeSwitch": "Ubiquiti Default",
    "Ruckus": "Ruckus Default",
}


def _match_platform(text: str) -> str | None:
    t = text.lower()
    for key, name in PLATFORM_MAP.items():
        if key in t:
            return name
    return None


def _apply_defaults(db: Session, device: Device, platform: str, user=None) -> None:
    if not device.ssh_credential_id:
        cred_name = DEFAULT_SSH_PROFILES.get(platform)
        if cred_name:
            cred = db.query(SSHCredential).filter(SSHCredential.name == cred_name).first()
            if cred:
                device.ssh_credential_id = cred.id
                device.ssh_profile_is_default = True
                log_audit(db, user, "auto_assign", device, f"Default SSH profile {cred_name}")


async def detect_snmp_platform(db: Session, device: Device, client: PyWrapper, user=None) -> None:
    try:
        descr = await client.get("1.3.6.1.2.1.1.1.0")
    except Exception:
        return
    if isinstance(descr, bytes):
        try:
            descr = descr.decode()
        except Exception:
            descr = descr.decode(errors="ignore")
    platform = _match_platform(str(descr))
    if platform and platform != device.detected_platform:
        device.detected_platform = platform
        device.detected_via = "SNMP sysDescr"
        _apply_defaults(db, device, platform, user)
        log_audit(db, user, "auto_detect", device, f"SNMP -> {platform}")
        db.commit()


async def detect_ssh_platform(db: Session, device: Device, conn, user=None) -> None:
    banner = conn.get_extra_info("server_version") or ""
    platform = _match_platform(banner)
    if platform and platform != device.detected_platform:
        device.detected_platform = platform
        device.detected_via = "SSH Banner"
        _apply_defaults(db, device, platform, user)
        log_audit(db, user, "auto_detect", device, f"SSH -> {platform}")
        db.commit()
