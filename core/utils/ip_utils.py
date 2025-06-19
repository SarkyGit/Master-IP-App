def pad_ip(ip: str) -> str:
    """Return zero-padded IP address string."""
    if not ip:
        return ""
    parts = ip.split('.')
    padded = [p.zfill(3) if p else '000' for p in parts]
    while len(padded) < 4:
        padded.append('000')
    return '.'.join(padded[:4])


def display_ip(ip: str) -> str:
    """Return IP string without zero padding."""
    if not ip:
        return ""
    return '.'.join(str(int(part)) for part in ip.split('.'))
