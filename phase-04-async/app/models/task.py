"""Database table at the final Alembic revision (0002)."""

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.schemas.task import TaskStatus


class Task(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: int = Field(default=0, ge=0, le=5)
