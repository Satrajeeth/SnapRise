from enum import Enum


class OtpPurpose(str, Enum):
    email_verification = "email_verification"
    password_reset = "password_reset"


class ChallengeStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    queued = "queued"
    verified = "verified"
    expired = "expired"
    blocked = "blocked"


class ProviderTier(str, Enum):
    free = "free"
    fallback = "fallback"


class AttemptResult(str, Enum):
    sent = "sent"
    failed = "failed"
    queued = "queued"


class ProviderErrorType(str, Enum):
    retryable = "retryable"
    non_retryable = "non_retryable"
    quota_exhausted = "quota_exhausted"
    auth_error = "auth_error"


class RetryJobStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
