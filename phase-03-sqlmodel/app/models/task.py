"""Database representation. API schemas live in app.schemas.task."""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.schemas.task import TaskStatus


class Task(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.TODO)
