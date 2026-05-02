from parity import is_even


def test_is_even_for_even_number() -> None:
    assert is_even(4) is True


def test_is_even_for_odd_number() -> None:
    assert is_even(3) is False
