"""Facts about saving, loading, foreign keys and indexes shown in the tutorial."""

from tutorials.n_plus_one import joined, lazy, select_in
from tutorials.relationship_facts import (
    back_populates_in_memory,
    insert_orphan,
    joined_rows,
    measure,
    query_plan,
    save_through_relationship,
)


def test_relationship_fills_project_id_on_save() -> None:
    statements, project_ids = save_through_relationship()
    assert statements[0].startswith("INSERT INTO demo_project")
    assert sum(sql.startswith("INSERT INTO demo_work_item") for sql in statements) == 2
    assert project_ids == [1, 1]


def test_back_populates_updates_the_other_side_without_sql() -> None:
    assert back_populates_in_memory() == (["目次を作る"], [])


def test_query_counts_grow_only_for_lazy_loading() -> None:
    assert measure(100, lazy)[0] == 101
    assert measure(100, select_in)[0] == 2
    assert measure(100, joined)[0] == 1


def test_selectinload_splits_a_long_in_list() -> None:
    assert measure(1000, select_in)[0] == 3


def test_joined_load_repeats_the_parent_row() -> None:
    assert joined_rows(projects=3, items_per_project=2) == (6, 3)


def test_sqlite_enforces_foreign_keys_only_when_enabled() -> None:
    assert insert_orphan(enforce=False) == "保存された"
    assert insert_orphan(enforce=True) == "IntegrityError: FOREIGN KEY constraint failed"


def test_index_changes_the_query_plan() -> None:
    assert query_plan(with_index=True)[0].startswith(
        "SEARCH demo_work_item USING INDEX ix_demo_work_item_project_id"
    )
    assert query_plan(with_index=False) == ["SCAN demo_work_item"]
