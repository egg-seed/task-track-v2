from quality_demo.progress import progress_percent


def test_half_done_is_50_percent() -> None:
    assert progress_percent(1, 2) == 50
