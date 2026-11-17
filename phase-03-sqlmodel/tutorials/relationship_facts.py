"""Measure how relationships are saved, loaded, constrained and indexed (Chapter 18).

Run from phase-03-sqlmodel:

    uv run python -m tutorials.relationship_facts

Every database here is in memory, so tasks.db is not touched.
"""

import time
from collections.abc import Callable

from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlmodel import Session, SQLModel, create_engine, select
from tutorials.n_plus_one import Report, create_demo_engine, joined, lazy, record_sql, select_in
from tutorials.relationships import Project, WorkItem

# 1. Saving related rows ------------------------------------------------------------


def save_through_relationship() -> tuple[list[str], list[int]]:
    """Attach items to a project object; SQLAlchemy fills in project_id when it flushes."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session, record_sql(engine) as statements:
        # SQLAlchemy fills in project_id when it flushes; mypy still sees it as required.
        items = [
            WorkItem(title="目次を作る"),  # type: ignore[call-arg]
            WorkItem(title="本文を書く"),  # type: ignore[call-arg]
        ]
        project = Project(name="本の執筆", items=items)
        session.add(project)
        session.commit()
        project_ids = [item.project_id for item in project.items]
    engine.dispose()
    return statements, project_ids


def back_populates_in_memory() -> tuple[list[str], list[str]]:
    """Setting item.project also updates project.items, before any SQL is sent."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session, record_sql(engine) as statements:
        project = Project(name="本の執筆")
        item = WorkItem(title="目次を作る")  # type: ignore[call-arg]
        item.project = project
        titles = [i.title for i in project.items]
        session.expunge_all()
    engine.dispose()
    return titles, statements


# 2. How the number of queries and the time grow --------------------------------------

STRATEGIES: dict[str, Callable[[Session], Report]] = {
    "lazy": lazy,
    "selectinload": select_in,
    "joinedload": joined,
}


def measure(projects: int, load: Callable[[Session], Report]) -> tuple[int, float]:
    """Return the number of queries and the best of 3 runs in milliseconds."""
    engine = create_demo_engine(projects=projects, items_per_project=2)
    best = float("inf")
    count = 0
    for _ in range(3):
        with Session(engine) as session, record_sql(engine) as statements:
            started = time.perf_counter()
            load(session)
            best = min(best, time.perf_counter() - started)
        count = len(statements)
    engine.dispose()
    return count, best * 1000


# 3. Rows returned by a joined load ----------------------------------------------------


def joined_rows(projects: int = 3, items_per_project: int = 2) -> tuple[int, int]:
    """Rows the JOIN returns, and objects left after unique()."""
    engine = create_demo_engine(projects=projects, items_per_project=items_per_project)
    statement = select(Project).options(joinedload(Project.items))  # type: ignore[arg-type]
    with Session(engine) as session:
        raw_rows = len(session.connection().execute(statement).all())
        unique_projects = len(session.exec(statement).unique().all())
    engine.dispose()
    return raw_rows, unique_projects


# 4. Foreign keys in SQLite ------------------------------------------------------------


def insert_orphan(*, enforce: bool) -> str:
    """Insert a work item whose project does not exist."""
    engine = create_engine("sqlite://")
    if enforce:

        def on_connect(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listen(engine, "connect", on_connect)
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add(WorkItem(project_id=999, title="親のない作業項目"))
            session.commit()
            return "保存された"
    except IntegrityError as exc:
        return f"{type(exc).__name__}: {exc.orig}"
    finally:
        engine.dispose()


# 5. Query plans with and without the index ---------------------------------------------

CHILD_QUERY = "SELECT * FROM demo_work_item WHERE project_id IN (1, 2, 3)"


def query_plan(*, with_index: bool) -> list[str]:
    engine = create_demo_engine(projects=3)
    with engine.begin() as connection:
        if not with_index:
            connection.execute(text("DROP INDEX ix_demo_work_item_project_id"))
        rows = connection.execute(text(f"EXPLAIN QUERY PLAN {CHILD_QUERY}")).all()
    engine.dispose()
    return [str(row[-1]) for row in rows]


def main() -> None:
    print("1. 関連データの保存")
    statements, project_ids = save_through_relationship()
    for sql in statements:
        print(f"   {sql}")
    print(f"   作業項目の project_id: {project_ids}")
    titles, sent = back_populates_in_memory()
    print(
        f"   item.project = project の直後の project.items: {titles}（送った SQL: {len(sent)}件）"
    )

    print("\n2. プロジェクトの数を増やしたときの SQL の回数と時間（3回の最小、ミリ秒）")
    for projects in (10, 100, 1000):
        cells = []
        for label, load in STRATEGIES.items():
            count, ms = measure(projects, load)
            cells.append(f"{label} {count}回 {ms:.1f}ms")
        print(f"   {projects:>4}件: " + " / ".join(cells))

    print("\n3. joinedload の JOIN が返す行（プロジェクト3件、各2件）")
    raw_rows, unique_projects = joined_rows()
    print(f"   JOIN の結果: {raw_rows}行 -> unique() の後: プロジェクト{unique_projects}件")

    print("\n4. SQLite で、存在しないプロジェクトを参照する作業項目を保存する")
    print(f"   既定（foreign_keys=OFF）: {insert_orphan(enforce=False)}")
    print(f"   PRAGMA foreign_keys=ON: {insert_orphan(enforce=True)}")

    print(f"\n5. {CHILD_QUERY} の実行計画")
    print(f"   インデックスあり: {query_plan(with_index=True)}")
    print(f"   インデックスなし: {query_plan(with_index=False)}")


if __name__ == "__main__":
    main()
