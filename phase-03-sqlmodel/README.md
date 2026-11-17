# Phase 03 — SQLModelとRepository

Phase 02と同じTask APIをSQLiteへ永続化します。**SQLModelのテーブルモデル**と**Pydantic APIスキーマ**を分離し、RouterにはSQLを書かず、Repositoryから呼び出します。

## 起動とテスト

```bash
cd phase-03-sqlmodel
uv sync --locked
uv run fastapi dev
# 別ターミナル
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

通常起動では`tasks.db`に保存されます。テストでは`StaticPool`を用いたインメモリSQLiteをテストごとに作成し、`create_app(test_engine)`でテスト用エンジンを渡します。`get_session`は`request.app.state.db_engine`から接続先を取得するため、FastAPIの依存関係を上書きする必要はありません。RepositoryのテストはHTTPを経由せず、DBに直接問い合わせます。

Phase 03では学習のため`SQLModel.metadata.create_all()`を使用します。**スキーマ変更の運用はAlembicを導入するPhase 04で扱います**。Service層も業務ルールが増えるまで導入しません。

## この段階の構成

- `app/main.py`: Router登録とLifespan
- `app/models/task.py`: SQLModelテーブル
- `app/schemas/task.py`: HTTP API用スキーマ
- `app/db/session.py`: DBエンジンとSession
- `app/repositories/task.py`: DBへのCRUD
- `app/api/routes/tasks.py`: HTTP処理
- `tests/unit/`: Schema検証、教材の単体テスト
- `tests/integration/`: Repository・SQLiteテスト
- `tests/api/`: HTTP契約テスト

## テーブルモデルが確かめること・確かめないこと（第15章）

`tutorials/table_model_demo.py` は、`create_all()` が送る `CREATE TABLE`、コンストラクタと `model_validate()` の検証の違い、SQLiteが `VARCHAR(100)` の長さを強制しないこと、`create_all()` が既存テーブルに列を足さないことを表示します。DBは一時ディレクトリとメモリ上にだけ作るため、`tasks.db` には触れません。

```bash
uv run python -m tutorials.table_model_demo
```

## CRUDで送られるSQL（第16章）

`tutorials/crud_sql.py` は、1件のタスクを `add()`・`flush()`・`commit()`・`delete()` したときのオブジェクトの状態と送られたSQLを表示します。続けて、Repositoryの関数ごとに送られるSQLを表示します。

```bash
uv run python -m tutorials.crud_sql
```

## トランザクションと同時更新（第17章）

`tutorials/transactions.py` は、Task APIとは独立した教材用のテーブル（`demo_task_log`・`demo_note`）を使い、次を確かめます。

- 処理ごとに `commit()` すると途中の失敗で半端なデータが残り、最後にまとめて `commit()` すると何も残らない
- `commit()` に失敗したSessionは、`rollback()` するまで使えない（`PendingRollbackError`）
- 2つのSessionが同じタスクを読んでから更新すると、先の変更が消える（lost update）
- `version` 列で更新前の版を確かめると、後の更新を検出でき、HTTPでは409にできる

```bash
uv run python -m tutorials.transactions
```

## リレーションシップとN+1問題（第18章）

`tutorials/` は、Task APIとは独立した1対多の例（Project・WorkItem）です。`tutorials/n_plus_one.py` を実行すると、関連の読み込み方ごとに発行されるSQLと、その回数を表示します。

```bash
uv run python -m tutorials.n_plus_one
```

- 既定の遅延読み込み：1 + N 回（N＝プロジェクトの数）
- `selectinload`：2回（`WHERE project_id IN (...)` でまとめて読む）
- `joinedload`：1回（`LEFT OUTER JOIN`。結果に `unique()` が必要）

`tests/integration/test_n_plus_one.py` は、この回数をテストで確かめます。`raiseload` で、隠れた遅延読み込みをエラーにする例も含みます。

`tutorials/relationship_facts.py` は、関連を通した保存で送られるSQL、プロジェクトの数を増やしたときのSQLの回数と時間、`joinedload` のJOINが返す行数、SQLiteで外部キーが強制されるかどうか、インデックスの有無による実行計画の違いを表示します。

```bash
uv run python -m tutorials.relationship_facts
```

## テストの教材（第24章・第25章）

`tutorials/memory_db_threads.py` は、テスト用のインメモリSQLiteを `StaticPool` と `check_same_thread=False` で作る理由を確かめます。既定のまま・`StaticPool` だけ・両方を指定、の3つのEngineで `TestClient` から `POST /tasks` を送り、結果と、接続を作ったスレッドを表示します。

```bash
uv run python -m tutorials.memory_db_threads
```

`tutorials/error_order.py` は、存在しないIDと不正な本文を同時に送ったとき、404と422のどちらが返るかを表示します。422を返した後に、タスクが変わっていないことも確かめます。

```bash
uv run python -m tutorials.error_order
```
