import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def get_fernet() -> Fernet:
    # Derive a 32-byte urlsafe key from Settings SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_password(password: str) -> str:
    if not password:
        return ""
    f = get_fernet()
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted_pw: str) -> str:
    if not encrypted_pw:
        return ""
    f = get_fernet()
    return f.decrypt(encrypted_pw.encode()).decode()
