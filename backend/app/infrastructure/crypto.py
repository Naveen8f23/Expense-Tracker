import os
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy.types import LargeBinary, TypeDecorator

_DEFAULT_KEY_PATH = Path(__file__).resolve().parents[2] / "data" / "secret.key"


def _key_path() -> Path:
    return Path(os.environ.get("ENCRYPTION_KEY_PATH", str(_DEFAULT_KEY_PATH)))


def _load_or_create_key() -> bytes:
    path = _key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_bytes()
    key = Fernet.generate_key()
    path.write_bytes(key)
    path.chmod(0o600)
    return key


def get_fernet() -> Fernet:
    return Fernet(_load_or_create_key())


class EncryptedText(TypeDecorator):
    """A text column that is transparently encrypted at rest (ADR-0015).

    Stored as ciphertext bytes; only ever plaintext in application memory after
    decryption on read, never on disk.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return get_fernet().encrypt(value.encode("utf-8"))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return get_fernet().decrypt(bytes(value)).decode("utf-8")
