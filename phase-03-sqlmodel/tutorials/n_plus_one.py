"""Show the N+1 query problem and how eager loading fixes it (Chapter 15).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.n_plus_one

The script uses an in-memory SQLite database and prints every SQL statement it runs.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, SQLModel, create_engine, select
from tutorials.relationships import Project, WorkItem

Report = list[tuple[str, int]]


def create_demo_engine(projects: int = 3, items_per_project: int = 2) -> Engine:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for p in range(1, projects + 1):
            project = Project(name=f"project {p}")
            session.add(project)
            session.flush()  # assigns project.id
            assert project.id is not None
            session.add_all(
                WorkItem(project_id=project.id, title=f"item {p}-{i}")
                for i in range(1, items_per_project + 1)
            )
        session.commit()
    return engine


@contextmanager
def record_sql(engine: Engine) -> Iterator[list[str]]:
    """Collect the SQL statements the engine sends while the block runs."""
    statements: list[str] = []

    def before_cursor_execute(*args: Any) -> None:
        statements.append(" ".join(str(args[2]).split()))

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def lazy(session: Session) -> Report:
    # Each access to project.items runs one more SELECT: 1 + N queries.
    projects = session.exec(select(Project)).all()
    return [(project.name, len(project.items)) for project in projects]


def select_in(session: Session) -> Report:
    # One SELECT for projects, one SELECT ... WHERE project_id IN (...) for all items.
    statement = select(Project).options(selectinload(Project.items))  # type: ignore[arg-type]
    projects = session.exec(statement).all()
    return [(project.name, len(project.items)) for project in projects]


def joined(session: Session) -> Report:
    # One SELECT with LEFT OUTER JOIN. unique() removes the repeated project rows.
    statement = select(Project).options(joinedload(Project.items))  # type: ignore[arg-type]
    projects = session.exec(statement).unique().all()
    return [(project.name, len(project.items)) for project in projects]


STRATEGIES: dict[str, Callable[[Session], Report]] = {
    "lazy (default)": lazy,
    "selectinload": select_in,
    "joinedload": joined,
}


def main() -> None:
    engine = create_demo_engine()
    for label, load in STRATEGIES.items():
        with Session(engine) as session, record_sql(engine) as statements:
            report = load(session)
        print(f"== {label}: {len(statements)} queries -> {report}")
        for sql in statements:
            print(f"   {sql}")
    engine.dispose()


if __name__ == "__main__":
    main()
