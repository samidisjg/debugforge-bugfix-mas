from counter import run_workers


def test_counter_reaches_expected_total() -> None:
    assert run_workers() == 2000
