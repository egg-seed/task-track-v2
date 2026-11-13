"""Independent one-to-many example; it does not alter the Task API."""

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "demo_project"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    items: list["WorkItem"] = Relationship(back_populates="project")  # noqa: UP037


class WorkItem(SQLModel, table=True):
    __tablename__ = "demo_work_item"
    __table_args__ = (Index("ix_demo_work_item_project_id", "project_id"),)

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="demo_project.id")
    title: str

    project: Project | None = Relationship(back_populates="items")
