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
- `tests/unit/`: Schema検証
- `tests/integration/`: Repository・SQLiteテスト
- `tests/api/`: HTTP契約テスト
