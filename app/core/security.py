"""Local encryption and hashing helpers for the token map."""
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _load_or_create_key() -> bytes:
    settings = get_settings()
    if settings.token_encryption_key:
        return settings.token_encryption_key.encode()

    key_file = settings.data_path / ".token_key"
    if key_file.exists():
        return key_file.read_bytes()

    key = Fernet.generate_key()
    key_file.write_bytes(key)
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt(value: str) -> str:
    """Encrypt a raw sensitive value for storage in the token map."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a stored token map value. Only called for authorized release."""
    return _fernet.decrypt(token.encode()).decode()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def short_hash(text: str, length: int = 10) -> str:
    return sha256(text)[:length]
