"""Relationship, foreign key, and eager-loading tutorial checks."""

from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, create_engine, select
from tutorials.relationships import Project, WorkItem


def test_project_items_relationship() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(name="book")
        session.add(project)
        session.flush()
        assert project.id is not None
        session.add_all(
            [
                WorkItem(project_id=project.id, title="chapter 14"),
                WorkItem(project_id=project.id, title="chapter 15"),
            ]
        )
        session.commit()

    with Session(engine) as session:
        statement = select(Project).options(selectinload(Project.items))  # type: ignore[arg-type]
        loaded = session.exec(statement).one()
        assert loaded.name == "book"
        assert {item.title for item in loaded.items} == {"chapter 14", "chapter 15"}
    engine.dispose()


def test_foreign_key_and_index_are_declared() -> None:
    table = SQLModel.metadata.tables["demo_work_item"]
    project_id = table.c["project_id"]
    assert {fk.target_fullname for fk in project_id.foreign_keys} == {"demo_project.id"}
    assert any("project_id" in [column.name for column in index.columns] for index in table.indexes)
