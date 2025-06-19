import re

MAC_RE = re.compile(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$')

def normalize_mac(mac: str | None) -> str | None:
    """Return MAC address in AA:BB:CC:DD:EE:FF format."""
    if not mac:
        return None
    hex_digits = re.sub(r'[^0-9a-fA-F]', '', mac)
    if len(hex_digits) != 12:
        return mac.upper()
    pairs = [hex_digits[i:i+2].upper() for i in range(0, 12, 2)]
    return ':'.join(pairs)

def display_mac(mac: str | None) -> str:
    if not mac:
        return ''
    return normalize_mac(mac) or ''

