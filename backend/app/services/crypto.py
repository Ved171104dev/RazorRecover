from __future__ import annotations
import base64,hashlib,os
from cryptography.fernet import Fernet,InvalidToken

class SecretConfigurationError(RuntimeError):pass

def _fernet()->Fernet:
    secret=os.getenv("CONNECTION_ENCRYPTION_KEY") or os.getenv("AUTH_SECRET")
    if not secret or len(secret)<24:
        raise SecretConfigurationError("Set CONNECTION_ENCRYPTION_KEY or AUTH_SECRET to at least 24 characters")
    key=base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)

def encrypt_secret(value:str)->str:return _fernet().encrypt(value.encode()).decode()
def decrypt_secret(value:str|None)->str|None:
    if not value:return None
    try:return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:raise SecretConfigurationError("Stored merchant credential cannot be decrypted with the configured encryption key") from exc
