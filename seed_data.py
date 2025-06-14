from app.utils.db_session import SessionLocal
from app.models.models import (
    DeviceType,
    SSHCredential,
    SNMPCommunity,
    Device,
    Location,
)


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
            snmp = SNMPCommunity(name="Home", community_string="homeSNMP", version="v2c")
            db.add(snmp)
            db.commit()

        # Seed default location
        loc = db.query(Location).filter_by(name="Main Site").first()
        if not loc:
            loc = Location(name="Main Site")
            db.add(loc)
            db.commit()

        # Seed device types
        switch_type = db.query(DeviceType).filter_by(name="Switch").first()
        if not switch_type:
            switch_type = DeviceType(name="Switch", manufacturer="Cisco")
            db.add(switch_type)

        ap_type = db.query(DeviceType).filter_by(name="AP").first()
        if not ap_type:
            ap_type = DeviceType(name="AP", manufacturer="Cisco")
            db.add(ap_type)

        camera_type = db.query(DeviceType).filter_by(name="IP Camera").first()
        if not camera_type:
            camera_type = DeviceType(name="IP Camera", manufacturer="Generic")
            db.add(camera_type)
        db.commit()

        # Seed sample switches if none exist
        if not db.query(Device).first():
            devices = [
                ("SW10.1", "192.168.10.1", "WS-C3560CX-12PC-S", "AT-1001"),
                ("SW10.2", "192.168.10.2", "WS-C2960G-8TC-L", "AT-1002"),
                ("SW10.6", "192.168.10.6", "WS-C2960C-12PC-L", "AT-1003"),
                ("SW10.10", "192.168.10.10", "WS-C3850-48P-E", "AT-1004"),
                ("SW10.11", "192.168.10.11", "WS-C3560CX-12PC-S", "AT-1005"),
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
                )
                db.add(device)
            db.commit()
            print("Sample data seeded")
        else:
            print("Sample devices already exist")
    finally:
        db.close()


if __name__ == "__main__":
    main()
