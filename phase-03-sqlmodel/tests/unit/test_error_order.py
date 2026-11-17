"""Request validation runs before the route looks the task up (Chapter 25)."""

import pytest
from tutorials.error_order import describe, main


def test_describe_lists_rejected_locations() -> None:
    body = {"detail": [{"loc": ["body", "title"], "msg": "too short"}]}
    assert describe(body) == "検証エラー: body.title"
    assert describe({"detail": "Task not found"}) == "{'detail': 'Task not found'}"


def test_main_prints_the_order(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "  -> 404 {'detail': 'Task not found'}"
    assert lines[3] == "  -> 422 検証エラー: body.title"
    assert lines[5] == "  -> 422 検証エラー: path.task_id"
    assert lines[7] == "  -> 422 検証エラー: body.title"
    assert lines[-1] == "422 の後のタスク: title='keep'（作成時と同じ: True）"
