import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a valid 32-byte Fernet key from the raw settings key.

    Fernet requires a url-safe base64-encoded 32-byte key.  We hash the
    user-supplied key with SHA-256 to guarantee exactly 32 bytes, then
    base64-encode the result.
    """
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key(settings.ENCRYPTION_KEY))


def encrypt_value(plaintext: str) -> str:
    """Encrypt *plaintext* and return a base64-encoded ciphertext string."""
    token: bytes = _fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded *ciphertext* and return the original plaintext."""
    plaintext: bytes = _fernet.decrypt(ciphertext.encode("utf-8"))
    return plaintext.decode("utf-8")


__all__ = ["encrypt_value", "decrypt_value"]
