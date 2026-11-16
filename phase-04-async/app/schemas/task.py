"""HTTP schemas are separate from SQLModel's database table."""

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
    priority: int = Field(default=0, ge=0, le=5)


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=5)

    @field_validator("title", "status", "priority")
    @classmethod
    def reject_explicit_null(cls, value: str | TaskStatus | int | None) -> str | TaskStatus | int:
        # Omission is valid; an explicit null for required DB columns is not.
        if value is None:
            raise ValueError("title, status and priority cannot be null")
        return value


class TaskRead(TaskCreate):
    id: UUID
