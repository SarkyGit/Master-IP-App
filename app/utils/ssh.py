import asyncssh

# Default SSH options to support legacy devices
SSH_OPTIONS = {
    # Disable host key checking
    "known_hosts": None,
    # Allow old key exchange algorithms
    "kex_algs": [
        "diffie-hellman-group14-sha1",
        "diffie-hellman-group1-sha1",
    ],
    # Include legacy encryption algorithms
    "encryption_algs": [
        "chacha20-poly1305@openssh.com",
        "aes256-gcm@openssh.com",
        "aes128-gcm@openssh.com",
        "aes256-ctr",
        "aes192-ctr",
        "aes128-ctr",
        "aes256-cbc",
        "aes192-cbc",
        "aes128-cbc",
        "3des-cbc",
    ],
    # Prefer common legacy host key algorithms
    "server_host_key_algs": [
        "ssh-rsa",
        "ssh-dss",
    ],
}


def build_conn_kwargs(cred):
    """Return asyncssh connection kwargs for the provided credential."""
    conn_kwargs = {"username": cred.username}
    if cred.password:
        conn_kwargs["password"] = cred.password
    if cred.private_key:
        try:
            conn_kwargs["client_keys"] = [asyncssh.import_private_key(cred.private_key)]
        except Exception:
            pass
    conn_kwargs.update(SSH_OPTIONS)
    return conn_kwargs
