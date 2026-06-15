"""Encrypt secrets at rest using a Fernet key derived from Django SECRET_KEY."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    try:
        return _fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except InvalidToken as exc:
        raise ValueError(
            'Failed to decrypt stored secret — SECRET_KEY may have changed.'
        ) from exc


def mask_secret(value: str, *, visible: int = 4) -> str:
    """Show only the last few characters for admin UI."""
    if not value:
        return ''
    if len(value) <= visible:
        return '•' * len(value)
    return f"{'•' * 12}…{value[-visible:]}"
