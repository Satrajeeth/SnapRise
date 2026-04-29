from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OtpHasher:
    @staticmethod
    def generate_code(length: int) -> str:
        minimum = 10 ** (length - 1)
        maximum = (10**length) - 1
        return str(secrets.randbelow(maximum - minimum + 1) + minimum)

    @staticmethod
    def new_salt() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def hash_code(code: str, salt: str) -> str:
        return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()

    @classmethod
    def create_hash(cls, code: str) -> tuple[str, str]:
        salt = cls.new_salt()
        return cls.hash_code(code, salt), salt

    @classmethod
    def verify(cls, code: str, expected_hash: str, salt: str) -> bool:
        return hmac.compare_digest(cls.hash_code(code, salt), expected_hash)


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked = local[:1] + "*"
    else:
        masked = local[:2] + "*" * max(1, len(local) - 2)
    return f"{masked}@{domain}"
