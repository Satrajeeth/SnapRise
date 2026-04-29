from datetime import datetime, timezone

from app.services.policies import BackoffPolicy


def test_backoff_policy_schedule_and_block():
    policy = BackoffPolicy(schedule=[30, 60, 120, 240], max_attempts=5)
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)

    assert int((policy.next_allowed_at(1, now) - now).total_seconds()) == 30
    assert int((policy.next_allowed_at(2, now) - now).total_seconds()) == 60
    assert int((policy.next_allowed_at(4, now) - now).total_seconds()) == 240
    assert policy.next_allowed_at(5, now) is None
    assert policy.is_blocked(5) is True
