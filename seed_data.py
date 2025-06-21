from core.utils.db_session import SessionLocal, reset_pk_sequence
import subprocess

from modules.inventory.models import Device, DeviceType, Location
from modules.network.models import SSHCredential, SNMPCommunity
from core.models.models import Site


def upgrade_db() -> None:
    """Apply any pending database migrations."""
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Warning: could not apply migrations: {exc}")


def main():
    db = SessionLocal()
    try:
        # Seed SSH credential
        cred = db.query(SSHCredential).filter_by(name="Home").first()
        if not cred:
            cred = SSHCredential(name="Home", username="admin", password="C0pperpa!r")
            db.add(cred)
            db.commit()

        # Seed SNMP community
        snmp = db.query(SNMPCommunity).filter_by(name="Home").first()
        if not snmp:
            snmp = SNMPCommunity(
                name="Home",
                community_string="homeSNMP",
                snmp_version="v2c",
                version=1,
            )
            db.add(snmp)
            db.commit()

        # Seed default location
        loc = db.query(Location).filter_by(name="Main Site").first()
        if not loc:
            loc = Location(name="Main Site", location_type="Fixed")
            db.add(loc)
            db.commit()

        site = db.query(Site).filter_by(name="Main Site").first()
        if not site:
            site = Site(name="Main Site", description="Default site")
            db.add(site)
            db.commit()

        # Seed device types
        switch_type = db.query(DeviceType).filter_by(name="Switch").first()
        if not switch_type:
            switch_type = DeviceType(name="Switch")
            db.add(switch_type)

        ap_type = db.query(DeviceType).filter_by(name="AP").first()
        if not ap_type:
            ap_type = DeviceType(name="AP")
            db.add(ap_type)

        camera_type = db.query(DeviceType).filter_by(name="IP Camera").first()
        if not camera_type:
            camera_type = DeviceType(name="IP Camera")
            db.add(camera_type)

        for dtype in ["PTP", "PTMP", "IPTV", "VOG", "IoT Device"]:
            if not db.query(DeviceType).filter_by(name=dtype).first():
                db.add(DeviceType(name=dtype))
        db.commit()

        # Seed sample switches if none exist
        if not db.query(Device).first():
            reset_pk_sequence(db, Device)
            devices = [
                ("SW10.1", "10.1.10.1", "WS-C3560CX-12PC-S", "AT-1001"),
                ("SW10.2", "10.1.10.2", "WS-C2960G-8TC-L", "AT-1002"),
                ("SW10.6", "10.1.10.6", "WS-C2960C-12PC-L", "AT-1003"),
                ("SW10.10", "10.1.10.10", "WS-C3850-48P-E", "AT-1004"),
                ("SW10.11", "10.1.10.11", "WS-C3560CX-12PC-S", "AT-1005"),
            ]
            for hostname, ip_address, model, atag in devices:
                device = Device(
                    hostname=hostname,
                    ip=ip_address,
                    asset_tag=atag,
                    model=model,
                    manufacturer="Cisco",
                    device_type_id=switch_type.id,
                    ssh_credential_id=cred.id,
                    snmp_community_id=snmp.id,
                    location_id=loc.id,
                    site_id=site.id,
                    config_pull_interval="none",
                )
                db.add(device)
            db.commit()
            reset_pk_sequence(db, Device)
            print("Sample data seeded")
        else:
            print("Sample devices already exist")
    finally:
        db.close()


if __name__ == "__main__":
    upgrade_db()
    main()
