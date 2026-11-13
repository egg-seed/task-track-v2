"""Task request/response schemas, independent of any database."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskStatus(StrEnum):
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus | None = None

    @field_validator("title", "status")
    @classmethod
    def reject_explicit_null(cls, value: str | TaskStatus | None) -> str | TaskStatus:
        # Omission is allowed; explicit null is not allowed for these fields.
        if value is None:
            raise ValueError("title and status cannot be null")
        return value


class TaskRead(TaskCreate):
    id: UUID
