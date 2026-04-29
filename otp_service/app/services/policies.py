from datetime import datetime, timedelta, timezone


class BackoffPolicy:
    def __init__(self, schedule: list[int], max_attempts: int):
        self.schedule = schedule
        self.max_attempts = max_attempts

    def next_allowed_at(self, attempt_count: int, now: datetime | None = None) -> datetime | None:
        if attempt_count <= 0:
            return None
        now = now or datetime.now(timezone.utc)
        if attempt_count >= self.max_attempts:
            return None
        index = min(attempt_count - 1, len(self.schedule) - 1)
        return now + timedelta(seconds=self.schedule[index])

    def is_blocked(self, attempt_count: int) -> bool:
        return attempt_count >= self.max_attempts
