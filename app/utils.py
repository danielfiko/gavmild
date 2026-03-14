

def read_secret(secret_name) -> str:
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        raise RuntimeError(f"Secret '{secret_name}' not found or unreadable")