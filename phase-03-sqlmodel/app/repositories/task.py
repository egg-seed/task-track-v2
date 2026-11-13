"""Task persistence: functions use a caller-owned Session."""

from uuid import UUID

from sqlmodel import Session, select

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskPatch, TaskStatus


def list_tasks(session: Session, status: TaskStatus | None = None) -> list[Task]:
    statement = select(Task)
    if status is not None:
        statement = statement.where(Task.status == status)
    return list(session.exec(statement).all())


def get_task(session: Session, task_id: UUID) -> Task | None:
    return session.get(Task, task_id)


def create_task(session: Session, data: TaskCreate) -> Task:
    task = Task.model_validate(data.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def update_task(session: Session, task: Task, data: TaskPatch) -> Task:
    task.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task: Task) -> None:
    session.delete(task)
    session.commit()
