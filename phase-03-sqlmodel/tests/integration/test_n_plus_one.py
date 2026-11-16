"""Count the SQL statements each loading strategy sends (Chapter 17)."""

from collections.abc import Callable

import pytest
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import raiseload
from sqlmodel import Session, select
from tutorials.n_plus_one import (
    Report,
    create_demo_engine,
    joined,
    lazy,
    main,
    record_sql,
    select_in,
)
from tutorials.relationships import Project

PROJECTS = 5
EXPECTED = [(f"project {p}", 2) for p in range(1, PROJECTS + 1)]


@pytest.mark.parametrize(
    ("load", "expected_queries"),
    [(lazy, 1 + PROJECTS), (select_in, 2), (joined, 1)],
    ids=["lazy", "selectinload", "joinedload"],
)
def test_query_count(load: Callable[[Session], Report], expected_queries: int) -> None:
    engine = create_demo_engine(projects=PROJECTS)
    with Session(engine) as session, record_sql(engine) as statements:
        assert load(session) == EXPECTED
    assert len(statements) == expected_queries
    engine.dispose()


def test_raiseload_turns_a_hidden_lazy_load_into_an_error() -> None:
    engine = create_demo_engine()
    with Session(engine) as session:
        statement = select(Project).options(raiseload(Project.items))  # type: ignore[arg-type]
        project = session.exec(statement).first()
        assert project is not None
        with pytest.raises(InvalidRequestError, match="lazy='raise'"):
            _ = project.items
    engine.dispose()


def test_script_prints_each_strategy(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    output = capsys.readouterr().out
    assert "== lazy (default): 4 queries" in output
    assert "== selectinload: 2 queries" in output
    assert "== joinedload: 1 queries" in output
