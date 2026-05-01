import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.users import UserManager


@pytest.mark.anyio
async def test_on_after_forgot_password_logs_request(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    manager = UserManager(MagicMock())
    user = SimpleNamespace(id="user-1", email="user@example.com")

    await manager.on_after_forgot_password(user, "token-abc")

    assert "User user-1 requested a password reset. Token: token-abc" in caplog.text
