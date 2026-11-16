"""Task persistence: coroutines use a caller-owned AsyncSession."""

from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskPatch, TaskStatus


async def list_tasks(session: AsyncSession, status: TaskStatus | None = None) -> list[Task]:
    statement = select(Task)
    if status is not None:
        statement = statement.where(Task.status == status)
    result = await session.exec(statement)
    return list(result.all())


async def get_task(session: AsyncSession, task_id: UUID) -> Task | None:
    return await session.get(Task, task_id)


async def create_task(session: AsyncSession, data: TaskCreate) -> Task:
    task = Task.model_validate(data.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task(session: AsyncSession, task: Task, data: TaskPatch) -> Task:
    task.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task: Task) -> None:
    await session.delete(task)
    await session.commit()
