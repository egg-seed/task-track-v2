# Phase 02: Router・Schemaに分割したタスク管理API

Phase 01と同じタスク管理APIを題材に、`main.py` をアプリケーションの初期化だけにして、`api/routes/` と `schemas/` を切り出したスナップショットです。

- `app/main.py`: アプリ生成とRouter登録
- `app/api/routes/`: HTTPエンドポイント
- `app/api/dependencies.py`: メモリ上のストアを注入する依存関係
- `app/schemas/task.py`: Pydanticスキーマ
- `tutorials/httpx_client.py`: 外部APIクライアントの教材（第19章）
- `tutorials/openapi_docs.py`: Swagger UIの表示を整える教材（第9章）。`uv run fastapi dev tutorials/openapi_docs.py` で起動し、`TASKS_SHOW_DOCS=false` を付けると `/docs` などを閉じる
- `tests/unit/`: スキーマ、教材の単体テスト
- `tests/api/`: HTTP契約テスト（依存関係の差し替えを含む）

```bash
cd phase-02-router
uv sync --locked
uv run fastapi dev
# 別ターミナルで
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

データはメモリ上にのみ保存します。永続化はPhase 03で扱います。
