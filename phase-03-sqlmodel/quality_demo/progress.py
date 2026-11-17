"""Four deliberate problems for Chapter 26: each tool finds a different one.

This directory is excluded from Ruff, mypy and pytest in CI. Check it on purpose:

    uv run ruff check quality_demo
    uv run ruff format --diff quality_demo
    uv run mypy quality_demo
    uv run pytest -q quality_demo
"""

import os

from app.schemas.task import TaskStatus


def count_done(statuses: list[TaskStatus]) -> int:
    return len([status for status in statuses if status == TaskStatus.DONE])


def progress_percent(done:int,total:int)->int:
    return done * 100 // (total + 1)


def progress_label(statuses: list[TaskStatus]) -> str:
    percent = progress_percent(count_done(statuses), len(statuses))
    return "進捗 " + percent + "%"
