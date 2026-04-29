import logging

from app.services.security import mask_email

logger = logging.getLogger("otp.audit")


class AuditLogger:
    def log(self, event: str, **kwargs) -> None:
        safe = dict(kwargs)
        if "email" in safe:
            safe["email"] = mask_email(str(safe["email"]))
        logger.info("%s | %s", event, safe)
