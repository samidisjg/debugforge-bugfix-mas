import pytest

from validator import normalize_age


def test_normalize_age_accepts_positive_values() -> None:
    assert normalize_age(18) == 18


def test_normalize_age_rejects_negative_values() -> None:
    with pytest.raises(ValueError):
        normalize_age(-2)
