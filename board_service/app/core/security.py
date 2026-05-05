import base64
import logging
from typing import Optional # It means the value can be of a given type or None

from cryptography.fernet import Fernet # Fernet is a symmetric encryption method that makes it easy to encrypt and decrypt data securely.
from cryptography.hazmat.primitives import hashes # This module provides various hashing algorithms.
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKF2HMAC # PBKDF2HMAC is a key derivation function that uses a password and a salt to generate a secure key. Salt means a random value added to the password to make it unique 

from app.config import settings

class EncryptionService:
    def __init__(self, key: Optional[str] = None):
        if not key :
            key = settings.encryption_key

        try: 
            #Fernet key must be 32 url-safe base64-encoded bytes
            self.fernet = Fernet(key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize EncryptionService: {e}")
            # For development, if key is invalid, we might want a fallback or to fail fast
            # In production, we MUST have a valid key
            raise RuntimeError("Invalid encryption key provided")
        
    def encrpt(self, data: str) -> str:
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
