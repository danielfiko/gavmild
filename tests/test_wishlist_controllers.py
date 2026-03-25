from datetime import datetime, timezone

import pytest

from app.auth.models import User
from app.wishlist.controllers import calculate_expires_at


def _user_with_birthday(month: int, day: int) -> User:
    """Build an unsaved User whose date_of_birth has the given month/day."""
    user = User()
    user.date_of_birth = datetime(1990, month, day)
    return user


class TestCalculateExpiresAtChristmas:
    def test_returns_december_24(self) -> None:
        user = _user_with_birthday(1, 15)
        result = calculate_expires_at("christmas", user)
        assert result.month == 12
        assert result.day == 24

    def test_result_is_timezone_aware(self) -> None:
        user = _user_with_birthday(1, 15)
        result = calculate_expires_at("christmas", user)
        assert result.tzinfo is not None

    def test_returns_future_date(self) -> None:
        user = _user_with_birthday(1, 15)
        result = calculate_expires_at("christmas", user)
        assert result > datetime.now(timezone.utc)


class TestCalculateExpiresAtBirthday:
    def test_returns_future_birthday(self) -> None:
        # Dec 31 is always in the future from any point in the year before it
        user = _user_with_birthday(12, 31)
        result = calculate_expires_at("birthday", user)
        assert result.month == 12
        assert result.day == 31
        assert result > datetime.now(timezone.utc)

    def test_result_is_timezone_aware(self) -> None:
        user = _user_with_birthday(6, 15)
        result = calculate_expires_at("birthday", user)
        assert result.tzinfo is not None

    def test_feb29_resolves_to_valid_date(self) -> None:
        user = User()
        user.date_of_birth = datetime(1992, 2, 29)  # 1992 is a leap year
        result = calculate_expires_at("birthday", user)
        # Must land on Feb 28 or 29 depending on whether the target year is a leap year
        assert result.month == 2
        assert result.day in (28, 29)
        assert result > datetime.now(timezone.utc)


class TestCalculateExpiresAtCustom:
    def test_returns_provided_date(self) -> None:
        user = _user_with_birthday(1, 15)
        custom = datetime(2030, 6, 15, tzinfo=timezone.utc)
        result = calculate_expires_at("custom", user, custom_date=custom)
        assert result == custom

    def test_naive_custom_date_gets_utc_tzinfo(self) -> None:
        user = _user_with_birthday(1, 15)
        naive = datetime(2030, 6, 15)  # no tzinfo
        result = calculate_expires_at("custom", user, custom_date=naive)
        assert result.tzinfo is not None

    def test_raises_value_error_when_no_custom_date(self) -> None:
        user = _user_with_birthday(1, 15)
        with pytest.raises(ValueError):
            calculate_expires_at("custom", user)


class TestCalculateExpiresAtUnknown:
    def test_raises_value_error_for_unknown_template(self) -> None:
        user = _user_with_birthday(1, 15)
        with pytest.raises(ValueError, match="Unknown template"):
            calculate_expires_at("unknown", user)

    def test_raises_value_error_for_empty_string(self) -> None:
        user = _user_with_birthday(1, 15)
        with pytest.raises(ValueError):
            calculate_expires_at("", user)
