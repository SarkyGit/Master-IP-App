import requests


def geolocate_ip(ip: str) -> tuple[str | None, float | None, float | None]:
    """Return location text and coordinates for the given IP using ipapi.co."""
    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            city = data.get("city")
            region = data.get("region")
            country = data.get("country_name")
            lat = data.get("latitude")
            lon = data.get("longitude")
            parts = [p for p in [city, region, country] if p]
            location = ", ".join(parts) if parts else None
            return location, lat, lon
    except Exception:
        pass
    return None, None, None
