import os

from app.schemas.task import TaskStatus


def count_done(statuses: list[TaskStatus]) -> int:
    return len([status for status in statuses if status == TaskStatus.DONE])


def progress_percent(done:int,total:int)->int:
    return done * 100 // (total + 1)


def progress_label(statuses: list[TaskStatus]) -> str:
    percent = progress_percent(count_done(statuses), len(statuses))
    return "進捗 " + percent + "%"
