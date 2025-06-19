import re

IP_RE = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def normalize_ip(ip: str) -> str:
    """Return normalized IPv4 string or raise ValueError if invalid."""
    if not ip:
        return ""
    ip = ip.strip()
    if not IP_RE.fullmatch(ip):
        raise ValueError("Invalid IP address")
    return ".".join(str(int(part)) for part in ip.split("."))


def pad_ip(ip: str) -> str:
    """Return zero-padded IP address string."""
    if not ip:
        return ""
    try:
        ip = normalize_ip(ip)
    except ValueError:
        return ""
    parts = ip.split(".")
    return ".".join(part.zfill(3) for part in parts)


def display_ip(ip: str) -> str:
    """Return IP string without zero padding."""
    if not ip:
        return ""
    return '.'.join(str(int(part)) for part in ip.split('.'))

