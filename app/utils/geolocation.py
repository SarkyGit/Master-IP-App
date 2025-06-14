import requests


def geolocate_ip(ip: str) -> str | None:
    """Return a simple location string for the given IP using ipapi.co."""
    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            city = data.get("city")
            region = data.get("region")
            country = data.get("country_name")
            parts = [p for p in [city, region, country] if p]
            if parts:
                return ", ".join(parts)
    except Exception:
        pass
    return None
