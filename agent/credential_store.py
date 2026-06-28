import argparse
import getpass
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def credential_file() -> Path:
    return Path(os.getenv("PORTAL_CREDENTIALS_FILE", "~/.careercaddy/portal_credentials.enc")).expanduser()


def _fernet() -> Fernet:
    key = os.getenv("PORTAL_CREDENTIALS_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTAL_CREDENTIALS_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def load_credentials() -> dict[str, dict[str, str]]:
    path = credential_file()
    if not path.exists():
        return {}
    try:
        decrypted = _fernet().decrypt(path.read_bytes())
        value = json.loads(decrypted.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("The local portal credential store could not be decrypted") from exc
    return value if isinstance(value, dict) else {}


def save_credentials(credentials: dict[str, dict[str, str]]) -> None:
    path = credential_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_fernet().encrypt(json.dumps(credentials).encode("utf-8")))


def get_portal_credentials(portal: str) -> dict[str, str]:
    return dict(load_credentials().get((portal or "generic").lower(), {}))


def set_portal_credentials(portal: str, username: str, password: str) -> None:
    credentials = load_credentials()
    credentials[portal.lower()] = {"username": username, "password": password}
    save_credentials(credentials)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage encrypted local portal credentials")
    parser.add_argument("portal", help="Portal key, for example greenhouse, lever, workday, or linkedin")
    args = parser.parse_args()
    username = input("Portal username/email: ").strip()
    password = getpass.getpass("Portal password: ")
    set_portal_credentials(args.portal, username, password)
    print(f"Saved encrypted credentials for {args.portal.lower()}.")


if __name__ == "__main__":
    main()
