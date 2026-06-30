from app.config import get_settings
from app.services.audit import AuditLogger
from app.services.cache import RedisCache
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.email_service import EmailService
from app.services.otp_service import OtpService
from app.services.policies import BackoffPolicy
from app.services.providers import ProviderRegistry
from app.services.quota import QuotaManager
from app.services.retry_dispatcher import RetryDispatcher
from app.services.routing import RoutingEngine

_otp_service = None
_email_service = None


def get_otp_service() -> OtpService:
    global _otp_service
    if _otp_service is None:
        settings = get_settings()
        cache = RedisCache()
        quota_manager = QuotaManager(cache)
        circuit_breaker = ProviderCircuitBreaker(
            cache=cache,
            failure_threshold=settings.provider_circuit_failure_threshold,
            open_seconds=settings.provider_circuit_open_seconds,
        )
        routing_engine = RoutingEngine(
            registry=ProviderRegistry(),
            quota_manager=quota_manager,
            circuit_breaker=circuit_breaker,
        )
        _otp_service = OtpService(
            settings=settings,
            routing_engine=routing_engine,
            retry_dispatcher=RetryDispatcher(
                retry_delay_seconds=settings.otp_retry_delay_seconds,
                max_jobs=settings.otp_retry_max_jobs,
            ),
            audit_logger=AuditLogger(),
            backoff_policy=BackoffPolicy(
                schedule=settings.otp_backoff_seconds,
                max_attempts=settings.otp_max_attempts,
            ),
            quota_manager=quota_manager,
        )
    return _otp_service


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        settings = get_settings()
        cache = RedisCache()
        quota_manager = QuotaManager(cache)
        circuit_breaker = ProviderCircuitBreaker(
            cache=cache,
            failure_threshold=settings.provider_circuit_failure_threshold,
            open_seconds=settings.provider_circuit_open_seconds,
        )
        routing_engine = RoutingEngine(
            registry=ProviderRegistry(),
            quota_manager=quota_manager,
            circuit_breaker=circuit_breaker,
        )
        _email_service = EmailService(settings=settings, routing_engine=routing_engine)
    return _email_service
