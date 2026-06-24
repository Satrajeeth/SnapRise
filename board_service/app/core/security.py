import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings

logger = logging.getLogger(__name__)

class EncryptionService:
    def __init__(self, key: Optional[str] = None):
        if not key:
            key = settings.encryption_key

        try:
            # Fernet key must be 32 url-safe base64-encoded bytes
            self.fernet = Fernet(key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize EncryptionService: {e}")
            raise RuntimeError("Invalid encryption key provided")

    def encrypt(self, data: str) -> str:
        """Encrypt a string and return the base64 encoded ciphertext."""
        if not data:
            return data
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a base64 encoded ciphertext and return the original string."""
        if not token:
            return token
        try:
            return self.fernet.decrypt(token.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return "[Decryption Failed]"

def get_encryption_service() -> EncryptionService:
    return EncryptionService()
