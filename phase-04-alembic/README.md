# Phase 04 — AlembicによるDBスキーマのバージョン管理

Phase 03のTodo APIを引き継ぎ、テーブル作成をアプリ起動時の `create_all()` からAlembicへ移します。

## 起動

```bash
cd phase-04-alembic
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev
```

`uv run alembic current` で適用済みリビジョンを確認できます。APIは従来のCRUDに加えて `priority`（0〜5、既定値0）を受け取ります。

## 2段階の履歴

- `0001_create_tasks.py`：Phase 03と同じTaskテーブルを作成
- `0002_add_task_priority.py`：既存データを消さずに `priority` を追加、未設定の既存行を0にする

手順は `uv run alembic upgrade head`。直前のスキーマを検証する場合は `uv run alembic downgrade 0001` を使用します。ただし実運用環境では事前バックアップと手順確認が必須です。

`TASKS_DATABASE_URL` 環境変数はFastAPI本体とAlembicで共通です。テストは実ファイルのSQLiteをテストごとに作成し、Alembicで初期化します。

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

`migrations/versions` のリビジョンは手動検証済みのコードとして保存しています。自動生成された変更は、適用前に必ずレビューします。フェーズは教育用サンプルであり、運用DBのバックアップ・復元や無停止変更を保証するものではありません。
